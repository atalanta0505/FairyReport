import { defineStore } from "pinia";
import { ref } from "vue";
import * as engineApi from "../lib/engineApi";
import type {
  ChapterInfo,
  GenericStatus,
  GenericUpdateResult,
  IngestResult,
  LLMConfig,
  MaterialOut,
  OutlineResult,
  ProjectOut,
  TemplateItem,
} from "../lib/engineApi";

export function parseChaptersFromOutline(outlineMd: string): ChapterInfo[] {
  if (!outlineMd) return [];
  const lines = outlineMd.split("\n");
  const chapters: ChapterInfo[] = [];
  let seq = 1;
  for (const line of lines) {
    const trimmed = line.trim();
    const match =
      trimmed.match(/^#{1,2}\s+(第[一二三四五六七八九十百零\d]+章[\s：:].+)/) ||
      trimmed.match(/^#{1,2}\s+(第[一二三四五六七八九十百零\d]+章.+)/) ||
      trimmed.match(/^(第[一二三四五六七八九十百零\d]+章[\s：:].+)/) ||
      trimmed.match(/^#\s+(.+)/);
    if (match) {
      chapters.push({ seq: seq++, title: match[1].trim() });
    }
  }
  return chapters;
}

export const useProjectStore = defineStore("project", () => {
  const currentStep = ref<number>(1);
  const projects = ref<ProjectOut[]>([]);
  const currentProject = ref<ProjectOut | null>(null);
  const materials = ref<MaterialOut[]>([]);
  const genericStatus = ref<GenericStatus | null>(null);

  // Step 2 大纲与模板状态
  const reportType = ref<string>("可行性研究报告");
  const templates = ref<TemplateItem[]>([]);
  const loadingTemplates = ref<boolean>(false);
  const outlineMd = ref<string>("");
  const outlineChapters = ref<ChapterInfo[]>([]);
  const generatingOutline = ref<boolean>(false);

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

  async function scanMaterials(
    baseUrl: string,
    projectName?: string,
  ): Promise<IngestResult[]> {
    const targetName = projectName || currentProject.value?.name;
    if (!baseUrl || !targetName) {
      throw new Error("请先选择项目");
    }
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

  async function loadTemplates(baseUrl: string): Promise<TemplateItem[]> {
    if (!baseUrl) return [];
    loadingTemplates.value = true;
    error.value = null;
    try {
      const list = await engineApi.getTemplates(baseUrl);
      templates.value = list;
      if (list.length > 0 && !list.find((t) => t.report_type === reportType.value)) {
        reportType.value = list[0].report_type;
      }
      return list;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      loadingTemplates.value = false;
    }
  }

  async function generateOutline(
    baseUrl: string,
    llmConfig: LLMConfig,
    reportTypeOverride?: string,
    projectNameOverride?: string,
  ): Promise<OutlineResult> {
    const targetProject = projectNameOverride !== undefined ? projectNameOverride : (currentProject.value?.name || "");
    const targetType = reportTypeOverride || reportType.value;
    if (!baseUrl) throw new Error("引擎未就绪");
    if (!targetType) throw new Error("请先选择报告类型");

    generatingOutline.value = true;
    error.value = null;
    try {
      const res = await engineApi.generateOutline(baseUrl, {
        project: targetProject,
        report_type: targetType,
        llm_config: llmConfig,
      });
      outlineMd.value = res.outline_md;
      outlineChapters.value = res.chapters;
      return res;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      generatingOutline.value = false;
    }
  }

  function setOutlineMd(md: string) {
    outlineMd.value = md;
    outlineChapters.value = parseChaptersFromOutline(md);
  }

  function setReportType(type: string) {
    reportType.value = type;
  }

  return {
    currentStep,
    projects,
    currentProject,
    materials,
    genericStatus,
    reportType,
    templates,
    loadingTemplates,
    outlineMd,
    outlineChapters,
    generatingOutline,
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
    scanMaterials,
    deleteMaterial,
    checkGenericStatus,
    updateGeneric,
    loadTemplates,
    generateOutline,
    setOutlineMd,
    setReportType,
  };
});
