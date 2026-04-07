import { create } from "zustand";

export interface VariableMapping {
  sourceVar: string;
  targetVar: string;
  type: "numerical" | "categorical" | "date" | "text";
  description?: string;
}

export interface ModelConfig {
  id: string;
  name: string;
  description: string;
  requiredVariables: {
    name: string;
    type: "numerical" | "categorical" | "date" | "text";
    description: string;
  }[];
}

interface ModelState {
  // Variable mapping
  mappings: VariableMapping[];
  availableSourceVars: string[];
  selectedModel: ModelConfig | null;

  // Actions
  setMappings(mappings: VariableMapping[]): void;
  addMapping(mapping: VariableMapping): void;
  removeMapping(index: number): void;
  updateMapping(index: number, mapping: Partial<VariableMapping>): void;
  setAvailableSourceVars(vars: string[]): void;
  setSelectedModel(model: ModelConfig | null): void;
  clearMappings(): void;
}

const DEFAULT_MODELS: ModelConfig[] = [
  {
    id: "panel-fe",
    name: "Panel Fixed Effects",
    description: "面板固定效应模型",
    requiredVariables: [
      { name: "entity_id", type: "categorical", description: "个体标识变量" },
      { name: "time_period", type: "date", description: "时间期" },
      { name: "dependent_var", type: "numerical", description: "因变量" },
      { name: "independent_var", type: "numerical", description: "自变量" },
    ],
  },
  {
    id: "did",
    name: "Difference-in-Differences",
    description: "双重差分模型",
    requiredVariables: [
      { name: "treatment", type: "categorical", description: "处理组标识" },
      { name: "post", type: "categorical", description: "政策实施前后" },
      { name: "dependent_var", type: "numerical", description: "因变量" },
      { name: "controls", type: "numerical", description: "控制变量" },
    ],
  },
  {
    id: "stirpat",
    name: "STIRPAT",
    description: "STIRPAT 模型（碳排放驱动分析）",
    requiredVariables: [
      { name: "carbon_emission", type: "numerical", description: "碳排放量" },
      { name: "population", type: "numerical", description: "人口规模" },
      { name: "gdp_per_capita", type: "numerical", description: "人均GDP" },
      { name: "energy_intensity", type: "numerical", description: "能源强度" },
    ],
  },
];

export const useModelStore = create<ModelState>((set) => ({
  mappings: [],
  availableSourceVars: [],
  selectedModel: DEFAULT_MODELS[0],

  setMappings: (mappings) => set({ mappings }),

  addMapping: (mapping) =>
    set((state) => ({ mappings: [...state.mappings, mapping] })),

  removeMapping: (index) =>
    set((state) => ({
      mappings: state.mappings.filter((_, i) => i !== index),
    })),

  updateMapping: (index, update) =>
    set((state) => ({
      mappings: state.mappings.map((m, i) => (i === index ? { ...m, ...update } : m)),
    })),

  setAvailableSourceVars: (vars) => set({ availableSourceVars: vars }),

  setSelectedModel: (model) => set({ selectedModel: model }),

  clearMappings: () => set({ mappings: [] }),
}));

export { DEFAULT_MODELS };
