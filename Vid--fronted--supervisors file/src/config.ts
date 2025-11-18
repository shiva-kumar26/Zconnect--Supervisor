// config.ts - FINAL VERSION: NO COOKIES, NO REDIRECT FROM KNOWLEDGE BASE, KB WORKS STABLY
import axios from "axios";

//
// ORIGINAL CONFIG (PRESERVED FOR OTHER PARTS OF APP)
//
const userConfig = {
  sip: "sip:",
  webSocketServerURL: "wss://10.16.7.91:7443/ws",
};

export const agentStatus = [
  "Available",
  "On Break",
  "Available (On Demand)",
  "Logged Out",
];

export const dbConfig = {
  baseURL: "https://10.16.7.202:3000",
  emailTemplates: "email-templates",
  knowledgeArticles: "knowledge-articles",
  customers: "customers",
  interactions: "interactions",
};

export const backendConfig = {
  baseURL: "https://10.16.7.96",
  loginEndPoint: "/login/authenticate_Login_and_users",
  logoutEndPoint: "/login/logout",
  updateAgent: "/api/directory_search",
  setAgentStatus: "/Set-Agent-Status",
  getAgentStatus: "/Get-Agent-Status",
  agents: "/api/directory_search",
  queueName: "/api/api/queue_tests/1",
  customers: "/api/customers/",
  callInteractions: "/api/interactions/",
  port: ":5050",
};

export default userConfig;

//
// MAIN API
//
export const mainApi = axios.create({
  baseURL: dbConfig.baseURL,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

//
// KNOWLEDGE BASE API (LOCAL FLASK)
//
export const kbApi = axios.create({
  baseURL: "http://localhost:8083",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

//
// USER ROLES
//
export enum UserRole {
  ADMIN = "admin",
  AGENT = "agent",
  UNKNOWN = "unknown"
}

//
// AUTH DATA INTERFACE
//
interface AuthData {
  user_id?: string;
  extension?: string;
  userId?: string;
  role?: string;
  username?: string;
  email?: string;
  fullName?: string;
  fullname?: string;     // Added for login response
  firstname?: string;    // Added for fallback
  authenticated?: boolean;
}

//
// AUTH CACHE & SYNC
//
let _cachedAuth: AuthData | null = null;

export const syncAuth = (): AuthData | null => {
  if (_cachedAuth) return _cachedAuth;

  const storages = [localStorage, sessionStorage];
  const keys = ['auth', 'user', 'session', 'userData', 'loginDetails']; // Added loginDetails

  for (const storage of storages) {
    for (const key of keys) {
      const raw = storage.getItem(key);
      if (raw) {
        try {
          const parsed = JSON.parse(raw);
          if (parsed.user_id || parsed.fullname || parsed.username || parsed.extension || parsed.role) {
            _cachedAuth = parsed;
            console.log(`Auth synced from ${storage === localStorage ? 'localStorage' : 'sessionStorage'}.${key}:`, parsed);
            const json = JSON.stringify(parsed);
            localStorage.setItem('auth', json);
            sessionStorage.setItem('auth', json);
            return parsed;
          }
        } catch (e) { /* ignore */ }
      }
    }
  }
  return null;
};

//
// SET AUTH (ON LOGIN)
//
export const setAuthCookie = (loginData: any): AuthData => {
  const authData: AuthData = {
    user_id: loginData.user_id || loginData.fullname || loginData.username || loginData.firstname,
    extension: loginData.extension || '',
    userId: loginData.user_id || loginData.userId,
    role: loginData.role,
    username: loginData.username || loginData.user_id || loginData.fullname,
    email: loginData.email || '',
    fullName: loginData.fullName || loginData.fullname || loginData.username,
    firstname: loginData.firstname,
    authenticated: true,
  };
  const json = JSON.stringify(authData);
  localStorage.setItem('auth', json);
  sessionStorage.setItem('auth', json);
  _cachedAuth = authData;
  console.log('Auth saved to localStorage + sessionStorage:', authData);
  return authData;
};

//
// GET AUTH (CACHED + SYNCED)
//
export const getAuthData = (): AuthData | null => {
  return _cachedAuth || syncAuth();
};

//
// USER ROLE
//
export const getUserRole = (): UserRole => {
  const auth = getAuthData();
  if (!auth) return UserRole.UNKNOWN;
  const role = auth.role?.toLowerCase();
  if (role === "admin" || role === "administrator" || role === "supervisor") return UserRole.ADMIN;
  if (auth.extension || auth.user_id || auth.userId) return UserRole.AGENT;
  return UserRole.UNKNOWN;
};

//
// USER IDENTIFIER
//
export const getUserIdentifier = (): string | null => {
  const auth = getAuthData();
  if (!auth) return null;
  const role = getUserRole();
  if (role === UserRole.ADMIN) return auth.username || auth.email || auth.user_id || auth.fullname || "admin";
  if (role === UserRole.AGENT) return auth.extension || auth.user_id || auth.userId || null;
  return null;
};

export const isAdmin = (): boolean => getUserRole() === UserRole.ADMIN;
export const isAgent = (): boolean => getUserRole() === UserRole.AGENT;

//
// AUTH INTERCEPTOR: NO REDIRECT FROM KNOWLEDGE BASE
//
let _isRedirecting = false;

const attachAuth = (instance: any) => {
  instance.interceptors.request.use((config: any) => {
    const auth = getAuthData();
    const userId = getUserIdentifier();
    if (auth && userId && config.headers) {
      config.headers.Authorization = `Bearer ${userId}`;
      config.headers["X-User-Role"] = getUserRole();
      console.log("Auth headers attached:", { userId, role: getUserRole() });
    } else {
      console.warn("No auth data for request:", config.url);
    }
    return config;
  });

  instance.interceptors.response.use(
    (response: any) => response,
    (error: any) => {
      if (error.response?.status === 401) {
        const currentPath = window.location.pathname;

        // BLOCK REDIRECT IF IN KNOWLEDGE BASE
        if (currentPath.includes('/knowledge-base') || currentPath.includes('/kb')) {
          console.warn("401 in Knowledge Base → staying here, syncing auth...");
          syncAuth();
          return Promise.reject(error); // Let component handle (e.g. retry)
        }

        // ONLY REDIRECT IF NOT IN KB
        if (!_isRedirecting) {
          _isRedirecting = true;
          console.warn("Session expired. Redirecting to home...");
          localStorage.clear();
          sessionStorage.clear();
          _cachedAuth = null;
          setTimeout(() => {
            window.location.href = "/"; // Safe redirect
            _isRedirecting = false;
          }, 100);
        }
      }

      if (error.code === 'ERR_NETWORK') {
        console.error("Network error:", error.config?.baseURL);
      }

      return Promise.reject(error);
    }
  );
};

attachAuth(mainApi);
attachAuth(kbApi);

//
// EXPORT AUTH UTILS
//
export const authUtils = {
  getAuthData,
  getUserRole,
  getUserIdentifier,
  isAdmin,
  isAgent,
  setAuthCookie,
  syncAuth,
};

//
// KNOWLEDGE BASE API FUNCTIONS
//
export const uploadDocuments = async (files: File[]): Promise<any> => {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  try {
    const response = await kbApi.post('/process-files', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  } catch (error: any) {
    console.error('Upload failed:', error);
    throw new Error(error.response?.data?.error || 'Failed to upload documents');
  }
};

export const getDocuments = async (): Promise<any> => {
  try {
    const response = await kbApi.get('/chat-documents');
    return response.data;
  } catch (error: any) {
    console.error('Get documents failed:', error);
    throw new Error(error.response?.data?.error || 'Failed to fetch documents');
  }
};

export const deleteDocument = async (documentId: string): Promise<any> => {
  try {
    const response = await kbApi.delete(`/documents/${documentId}`);
    return response.data;
  } catch (error: any) {
    console.error('Delete failed:', error);
    throw new Error(error.response?.data?.error || 'Failed to delete document');
  }
};

export const reprocessDocument = async (documentId: string): Promise<any> => {
  try {
    const response = await kbApi.post(`/reprocess-document/${documentId}`);
    return response.data;
  } catch (error: any) {
    console.error('Reprocess failed:', error);
    throw new Error(error.response?.data?.error || 'Failed to reprocess document');
  }
};

export const markDocumentAsGlobal = async (documentId: string): Promise<any> => {
  try {
    const response = await kbApi.post(`/documents/${documentId}/mark-global`);
    return response.data;
  } catch (error: any) {
    console.error('Mark global failed:', error);
    throw new Error(error.response?.data?.error || 'Failed to mark document as global');
  }
};

export const unmarkDocumentAsGlobal = async (documentId: string): Promise<any> => {
  try {
    const response = await kbApi.post(`/documents/${documentId}/unmark-global`);
    return response.data;
  } catch (error: any) {
    console.error('Unmark global failed:', error);
    throw new Error(error.response?.data?.error || 'Failed to unmark document as global');
  }
};

export const sendChatMessage = async (message: string, files?: File[]): Promise<any> => {
  const formData = new FormData();
  formData.append('message', message);
  if (files?.length) files.forEach(file => formData.append('files', file));
  try {
    const response = await kbApi.post('/chat', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  } catch (error: any) {
    console.error('Chat failed:', error);
    throw new Error(error.response?.data?.error || 'Failed to send message');
  }
};

export const healthCheck = async (): Promise<any> => {
  try {
    const response = await kbApi.get('/health');
    return response.data;
  } catch (error: any) {
    console.error('Health check failed:', error);
    throw new Error('Health check failed');
  }
};

export const knowledgeBaseApi = {
  uploadDocuments,
  getDocuments,
  deleteDocument,
  reprocessDocument,
  markDocumentAsGlobal,
  unmarkDocumentAsGlobal,
  sendChatMessage,
  healthCheck,
};

//
// ================= KNOWLEDGE BASE MEMORY SESSION (SEPARATE FROM MAIN AUTH) =================
//
export const KBAuthSession = {
  userId: null as string | null,
  role: null as string | null,
  extension: null as string | null,

  syncFromMainAuth() {
    // Try sessionStorage first (where admin stores "loginDetails")
    const stored = sessionStorage.getItem("loginDetails") || localStorage.getItem('auth');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
       
        // FIXED: Your login returns "fullname", not "user_id"!
        this.userId = parsed.user_id || parsed.fullname || parsed.username || parsed.firstname;
        this.role = parsed.role?.toLowerCase();
        this.extension = parsed.extension || "";
       
        console.log("KB Session synced:", {
          userId: this.userId,
          role: this.role,
          extension: this.extension || "(none)",
          rawData: parsed // Debug: show what we got
        });
       
        if (!this.userId) {
          console.error("No user identifier found in:", Object.keys(parsed));
        }
       
        return;
      } catch (e) {
        console.error("Failed to sync KB session:", e);
      }
    }
   
    // Fallback: try cookie (if it exists)
    const cookie = document.cookie.split('; ').find(row => row.startsWith('user-data='));
    if (cookie) {
      try {
        const cookieValue = decodeURIComponent(cookie.split('=')[1]);
        const parsed = JSON.parse(cookieValue);
       
        this.userId = parsed.user_id || parsed.fullname || parsed.username;
        this.role = parsed.role?.toLowerCase();
        this.extension = parsed.extension || "";
       
        console.log("KB Session synced from cookie:", {
          userId: this.userId,
          role: this.role
        });
      } catch (e) {
        console.error("Failed to parse cookie:", e);
      }
    }
   
    if (!this.userId) {
      console.error("Failed to sync KB session - no user_id found");
    }
  },

  clear() {
    this.userId = null;
    this.role = null;
    this.extension = null;
    console.log("KB Session cleared");
  },

  isValid() {
    return !!this.userId && !!this.role;
  }
};

//
// ================= SEPARATE KB API INTERCEPTOR (DOESN'T AFFECT MAIN AUTH) =================
//
const attachKBOnlyAuth = (instance: any) => {
  instance.interceptors.request.use((config: any) => {
    // Try to sync if not valid
    if (!KBAuthSession.isValid()) {
      KBAuthSession.syncFromMainAuth();
    }

    if (KBAuthSession.isValid()) {
      config.headers["X-User-Id"] = KBAuthSession.userId;
      config.headers["X-User-Role"] = KBAuthSession.role;
      
      // For admin without extension, send user_id as extension
      config.headers["X-Extension"] = KBAuthSession.extension || KBAuthSession.userId;
      
      console.log("KB Auth Headers Sent:", {
        "X-User-Id": KBAuthSession.userId,
        "X-User-Role": KBAuthSession.role,
        "X-Extension": KBAuthSession.extension || KBAuthSession.userId
      });
    } else {
      console.warn("KB Session invalid - headers not attached");
    }
    return config;
  });

  instance.interceptors.response.use(
    (res) => res,
    (err) => {
      if (err.response?.status === 401) {
        console.error("KB API 401 - re-syncing auth");
        KBAuthSession.syncFromMainAuth();
      }
      return Promise.reject(err);
    }
  );
};

// Apply ONLY to KB API (not mainApi)
attachKBOnlyAuth(kbApi);