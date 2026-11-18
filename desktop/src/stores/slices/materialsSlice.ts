import * as engineApi from "../../lib/engineApi";
import type {
  GenericStatus,
  GenericUpdateResult,
  IngestResult,
  MaterialOut,
} from "../../lib/engineApi";
import type { ProjectStoreState } from "./types";

export function createMaterialsSlice(state: ProjectStoreState) {
  const {
    currentProject,
    materials,
    genericStatus,
    loadingMaterials,
    ingesting,
    updatingGeneric,
    error,
  } = state;

  function requireProjectTarget(baseUrl: string, projectName?: string): string {
    const targetName = projectName || currentProject.value?.name;
    if (!baseUrl || !targetName) {
      throw new Error("请先选择项目");
    }
    return targetName;
  }

  async function loadMaterials(baseUrl: string, projectName?: string): Promise<MaterialOut[]> {
    const targetName = projectName || currentProject.value?.name;
    if (!baseUrl || !targetName) {
      materials.value = [];
      return [];
    }
    loadingMaterials.value = true;
    error.value = null;
    try {
      const list = await engineApi.listMaterials(baseUrl, targetName);
      materials.value = list;
      return list;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      loadingMaterials.value = false;
    }
  }

  async function ingestFiles(
    baseUrl: string,
    filePaths: string[],
    projectName?: string,
  ): Promise<IngestResult[]> {
    const targetName = requireProjectTarget(baseUrl, projectName);
    if (!filePaths || filePaths.length === 0) return [];

    ingesting.value = true;
    error.value = null;
    try {
      const isRemote = !baseUrl.includes("127.0.0.1") && !baseUrl.includes("localhost");
      let results: IngestResult[];

      if (isRemote) {
        const { invoke } = await import("@tauri-apps/api/core");
        const uploadItems: engineApi.UploadFileItem[] = [];
        const chunkSize = 8192;

        for (const fpath of filePaths) {
          const filename = fpath.replace(/^.*[\\\/]/, "");
          const bytes = await invoke<number[] | Uint8Array>("read_file_binary", { path: fpath });
          const u8 = new Uint8Array(bytes);
          let binary = "";
          for (let i = 0; i < u8.length; i += chunkSize) {
            const sub = u8.subarray(i, i + chunkSize);
            binary += String.fromCharCode.apply(null, sub as unknown as number[]);
          }
          uploadItems.push({ filename, content_base64: btoa(binary) });
        }
        results = await engineApi.uploadMaterials(baseUrl, targetName, uploadItems);
      } else {
        results = await engineApi.ingestMaterials(baseUrl, targetName, filePaths);
      }

      await loadMaterials(baseUrl, targetName);
      return results;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      ingesting.value = false;
    }
  }

  async function uploadFiles(
    baseUrl: string,
    items: engineApi.UploadFileItem[],
    projectName?: string,
  ): Promise<IngestResult[]> {
    const targetName = requireProjectTarget(baseUrl, projectName);
    if (!items || items.length === 0) return [];

    ingesting.value = true;
    error.value = null;
    try {
      const results = await engineApi.uploadMaterials(baseUrl, targetName, items);
      await loadMaterials(baseUrl, targetName);
      return results;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      ingesting.value = false;
    }
  }

  async function deleteMaterial(
    baseUrl: string,
    sourceId: string,
    projectName?: string,
  ): Promise<void> {
    const targetName = requireProjectTarget(baseUrl, projectName);
    error.value = null;
    try {
      await engineApi.deleteMaterial(baseUrl, targetName, sourceId);
      await loadMaterials(baseUrl, targetName);
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    }
  }

  async function scanMaterials(baseUrl: string, projectName?: string): Promise<IngestResult[]> {
    const targetName = requireProjectTarget(baseUrl, projectName);
    ingesting.value = true;
    error.value = null;
    try {
      const results = await engineApi.scanMaterials(baseUrl, targetName);
      await loadMaterials(baseUrl, targetName);
      return results;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      ingesting.value = false;
    }
  }

  async function openProjectDir(
    baseUrl: string,
    projectName?: string,
  ): Promise<{ path: string }> {
    const targetName = requireProjectTarget(baseUrl, projectName);
    error.value = null;
    try {
      return await engineApi.openProjectDir(baseUrl, targetName);
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    }
  }

  async function checkGenericStatus(baseUrl: string): Promise<GenericStatus> {
    if (!baseUrl) {
      genericStatus.value = null;
      return { installed: false };
    }
    try {
      const status = await engineApi.getGenericStatus(baseUrl);
      genericStatus.value = status;
      return status;
    } catch {
      genericStatus.value = { installed: false };
      return { installed: false };
    }
  }

  async function updateGeneric(
    baseUrl: string,
    serverUrl: string,
    token: string,
  ): Promise<GenericUpdateResult> {
    if (!baseUrl) throw new Error("引擎未就绪");
    updatingGeneric.value = true;
    error.value = null;
    try {
      const res = await engineApi.updateGenericKnowledge(baseUrl, serverUrl, token);
      await checkGenericStatus(baseUrl);
      return res;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      updatingGeneric.value = false;
    }
  }

  return {
    loadMaterials,
    ingestFiles,
    uploadFiles,
    deleteMaterial,
    scanMaterials,
    openProjectDir,
    checkGenericStatus,
    updateGeneric,
  };
}
