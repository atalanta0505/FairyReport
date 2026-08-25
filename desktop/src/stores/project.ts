import { defineStore } from "pinia";
import { ref } from "vue";
import * as engineApi from "../lib/engineApi";
import type {
  GenericStatus,
  GenericUpdateResult,
  IngestResult,
  MaterialOut,
  ProjectOut,
} from "../lib/engineApi";

export const useProjectStore = defineStore("project", () => {
  const currentStep = ref<number>(1);
  const projects = ref<ProjectOut[]>([]);
  const currentProject = ref<ProjectOut | null>(null);
  const materials = ref<MaterialOut[]>([]);
  const genericStatus = ref<GenericStatus | null>(null);

  const loadingProjects = ref<boolean>(false);
  const loadingMaterials = ref<boolean>(false);
  const ingesting = ref<boolean>(false);
  const updatingGeneric = ref<boolean>(false);
  const error = ref<string | null>(null);

  function setStep(step: number) {
    if (step >= 1 && step <= 5) {
      currentStep.value = step;
    }
  }

  async function loadProjects(baseUrl: string) {
    if (!baseUrl) return;
    loadingProjects.value = true;
    error.value = null;
    try {
      const list = await engineApi.listProjects(baseUrl);
      projects.value = list;
      if (currentProject.value) {
        const found = list.find((p) => p.name === currentProject.value?.name);
        if (found) {
          currentProject.value = found;
        } else if (list.length > 0) {
          currentProject.value = list[0];
          await loadMaterials(baseUrl, list[0].name);
        } else {
          currentProject.value = null;
          materials.value = [];
        }
      } else if (list.length > 0) {
        currentProject.value = list[0];
        await loadMaterials(baseUrl, list[0].name);
      } else {
        currentProject.value = null;
        materials.value = [];
      }
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      loadingProjects.value = false;
    }
  }

  async function selectProject(baseUrl: string, projectName: string) {
    const p = projects.value.find((item) => item.name === projectName);
    if (p) {
      currentProject.value = p;
      await loadMaterials(baseUrl, projectName);
    }
  }

  async function createProject(baseUrl: string, name: string): Promise<ProjectOut> {
    if (!baseUrl) throw new Error("引擎未就绪");
    error.value = null;
    try {
      const created = await engineApi.createProject(baseUrl, name);
      await loadProjects(baseUrl);
      await selectProject(baseUrl, created.name);
      return created;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    }
  }

  async function deleteProject(baseUrl: string, name: string): Promise<void> {
    if (!baseUrl) throw new Error("引擎未就绪");
    error.value = null;
    try {
      await engineApi.deleteProject(baseUrl, name);
      if (currentProject.value?.name === name) {
        currentProject.value = null;
        materials.value = [];
      }
      await loadProjects(baseUrl);
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    }
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
    const targetName = projectName || currentProject.value?.name;
    if (!baseUrl || !targetName) {
      throw new Error("请先选择项目");
    }
    if (!filePaths || filePaths.length === 0) {
      return [];
    }
    ingesting.value = true;
    error.value = null;
    try {
      const results = await engineApi.ingestMaterials(baseUrl, targetName, filePaths);
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
    const targetName = projectName || currentProject.value?.name;
    if (!baseUrl || !targetName) {
      throw new Error("请先选择项目");
    }
    error.value = null;
    try {
      await engineApi.deleteMaterial(baseUrl, targetName, sourceId);
      await loadMaterials(baseUrl, targetName);
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
    } catch (e) {
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
    currentStep,
    projects,
    currentProject,
    materials,
    genericStatus,
    loadingProjects,
    loadingMaterials,
    ingesting,
    updatingGeneric,
    error,
    setStep,
    loadProjects,
    selectProject,
    createProject,
    deleteProject,
    loadMaterials,
    ingestFiles,
    deleteMaterial,
    checkGenericStatus,
    updateGeneric,
  };
});
