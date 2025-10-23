import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8012";

export interface CompanyExtractionRequest {
  company_name: string;
  include_subsidiaries?: boolean;
  max_subsidiaries?: number;
  deep_search?: boolean;
}

export interface URLExtractionRequest {
  url: string;
  include_subsidiaries?: boolean;
  max_subsidiaries?: number;
  deep_search?: boolean;
}

export interface LocationInfo {
  label?: string | null;
  line1?: string | null;
  city?: string | null;
  country?: string | null;
  postal_code?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  sources?: SourceReference[];
}

// Alias pour compatibilité
export interface SiteInfo extends LocationInfo {
  notes?: string | null;
}

export interface SubsidiaryDetail {
  legal_name: string;
  headquarters?: LocationInfo | null;
  activity?: string | null;
  confidence?: number | null;
  sources: SourceReference[];
}

// Type pour la présence commerciale
export interface CommercialPresence {
  name: string;
  type: "office" | "partner" | "distributor" | "representative";
  relationship: "owned" | "partnership" | "authorized_distributor" | "franchise";
  activity?: string | null;
  location: LocationInfo;
  phone?: string | null;
  email?: string | null;
  confidence?: number | null;
  sources: SourceReference[];
  since_year?: number | null;
  status?: "active" | "inactive" | "unverified" | null;
}

export interface CompanyData {
  company_name: string;
  headquarters_address: string;
  headquarters_city?: string | null;
  headquarters_country?: string | null;
  parent_company?: string | null;
  sector: string;
  activities: string[];
  revenue_recent?: string | null;
  employees?: string | null;
  founded_year?: number | null;
  phone?: string | null;
  email?: string | null;
  subsidiaries_details: SubsidiaryDetail[];
  
  // 🆕 NOUVEAU : Présence commerciale
  commercial_presence_details: CommercialPresence[];
  
  sources: SourceReference[];
  methodology_notes?: string[] | null;
  extraction_metadata?: ExtractionMetadata | null;
  extraction_date?: string | null;
}

export interface SourceReference {
  title: string;
  url: string;
  publisher?: string | null;
  published_date?: string | null;
  tier: "official" | "financial_media" | "pro_db" | "other";
  accessibility?: "ok" | "protected" | "rate_limited" | "broken" | null;
}

export interface ParentReference {
  legal_name: string;
  relationship: string;
  jurisdiction?: string | null;
  sources?: SourceReference[];
}

export interface SourceQualityEntry {
  url: string;
  tier: string;
  score: number;
  freshness_days?: number | null;
  accessibility?: string | null;
}

export interface ExtractionMetadata {
  input_type?: string | null;
  session_id?: string | null;
  processing_time?: number | null;
}

export interface CoherenceAnalysis {
  geographic_score: number | null;
  structure_score: number | null;
  sources_score: number | null;
  overall_score: number | null;
  conflicts: string[];
}

export interface AgentConfidenceScore {
  agent_name: string;
  confidence: number;
  reasoning?: string | null;
}

export interface QualityIndicatorEntry {
  indicator_name: string;
  score: number;
  description?: string | null;
}

export interface AgentState {
  name: string;
  status: string;
  progress: number;
  message: string;
  started_at: string | null;
  updated_at: string | null;
  error_message: string | null;
  current_step?: number;
  total_steps?: number;
  step_name?: string;
  performance_metrics?: {
    elapsed_time?: number;
    steps_completed?: number;
    steps_remaining?: number;
    current_step_duration?: number;
    average_step_time?: number;
    estimated_total_time?: number;
  };
}

export interface ExtractionProgress {
  session_id: string;
  company_name: string;
  overall_status: string;
  overall_progress: number;
  agents: AgentState[];
  started_at: string;
  updated_at: string;
}

export interface AsyncExtractionResponse {
  session_id: string;
  status: "started" | "queued";
  message: string;
}

export interface HealthCheckResponse {
  status: string;
  timestamp: string;
  version: string;
  openai_agents_available: boolean;
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000, // 10 minutes for company extraction (optimized workflow)
  headers: {
    "Content-Type": "application/json",
  },
  // Configuration pour éviter les suspensions réseau
  maxRedirects: 5,
  validateStatus: function (status) {
    return status >= 200 && status < 300; // Accepte seulement les codes 2xx
  },
});

// Add request interceptor for logging
apiClient.interceptors.request.use((config) => {
  console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Add response interceptor for error handling with retry logic
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Gestion spécifique des erreurs réseau
    if (
      error.code === "NETWORK_ERROR" ||
      error.message.includes("ERR_NETWORK_IO_SUSPENDED") ||
      error.message.includes("Network Error")
    ) {
      console.warn(
        "🔄 Erreur réseau détectée, tentative de reconnexion...",
        error.message
      );

      // Retry logic pour les erreurs réseau
      if (!originalRequest._retry && originalRequest._retryCount < 3) {
        originalRequest._retry = true;
        originalRequest._retryCount = (originalRequest._retryCount || 0) + 1;

        // Attendre avant de retry (backoff exponentiel)
        const delay = Math.pow(2, originalRequest._retryCount) * 1000;
        console.log(
          `⏳ Retry ${originalRequest._retryCount}/3 dans ${delay}ms...`
        );

        await new Promise((resolve) => setTimeout(resolve, delay));
        return apiClient(originalRequest);
      }
    }

    console.error("API Error:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Heartbeat pour maintenir la connexion active pendant les longues requêtes
let heartbeatInterval: NodeJS.Timeout | null = null;

const startHeartbeat = () => {
  if (heartbeatInterval) return;

  heartbeatInterval = setInterval(async () => {
    try {
      await apiClient.get("/health", { timeout: 5000 });
      console.log("💓 Heartbeat OK");
    } catch (error) {
      console.warn("💓 Heartbeat failed:", error);
    }
  }, 30000); // Toutes les 30 secondes
};

const stopHeartbeat = () => {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
    heartbeatInterval = null;
    console.log("💓 Heartbeat arrêté");
  }
};

export const api = {
  // Health check
  async healthCheck(): Promise<HealthCheckResponse> {
    const response = await apiClient.get<HealthCheckResponse>("/health");
    return response.data;
  },

  // Extract company information by name (POST) - mode synchrone
  async extractCompany(data: CompanyExtractionRequest): Promise<CompanyData> {
    try {
      startHeartbeat(); // Démarrer le heartbeat
      const response = await apiClient.post<CompanyData>("/extract", data);
      stopHeartbeat(); // Arrêter le heartbeat
      return response.data;
    } catch (error) {
      stopHeartbeat(); // Arrêter le heartbeat en cas d'erreur
      throw error;
    }
  },

  // Extract company information from URL - mode synchrone
  async extractFromURL(data: URLExtractionRequest): Promise<CompanyData> {
    try {
      startHeartbeat(); // Démarrer le heartbeat
      const response = await apiClient.post<CompanyData>(
        "/extract-from-url",
        data
      );
      stopHeartbeat(); // Arrêter le heartbeat
      return response.data;
    } catch (error) {
      stopHeartbeat(); // Arrêter le heartbeat en cas d'erreur
      throw error;
    }
  },

  // Extract company information by name (POST) - mode asynchrone
  async startExtractionAsync(
    data: CompanyExtractionRequest
  ): Promise<AsyncExtractionResponse> {
    const response = await apiClient.post<AsyncExtractionResponse>(
      "/extract-async",
      data
    );
    return response.data;
  },

  // Extract company information from URL - mode asynchrone
  async startExtractionFromURLAsync(
    data: URLExtractionRequest
  ): Promise<AsyncExtractionResponse> {
    const response = await apiClient.post<AsyncExtractionResponse>(
      "/extract-from-url-async",
      data
    );
    return response.data;
  },

  // Get API root information
  async getApiInfo(): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>("/");
    return response.data;
  },

  // Endpoints pour le suivi temps réel
  // Get session status
  async getSessionStatus(sessionId: string): Promise<ExtractionProgress> {
    const response = await apiClient.get<ExtractionProgress>(
      `/status/${sessionId}`
    );
    return response.data;
  },

  // Get extraction results
  async getExtractionResults(sessionId: string): Promise<CompanyData> {
    const response = await apiClient.get<CompanyData>(`/results/${sessionId}`);
    return response.data;
  },
};

export default api;
