import React, { createContext, useContext, useState, ReactNode, useEffect } from 'react';
import axios from 'axios';
import { AuthState, User } from '../types/auth';

const AuthContext = createContext<{
  authState: AuthState;
  login: (user: User) => void;
  logout: () => void;
  loading: boolean;
  updateUserStatus: (newStatus: string) => void;
  refreshAgents: () => Promise<void>;
}>({
  authState: { user: null, isAuthenticated: false },
  login: () => {},
  logout: () => {},
  updateUserStatus: () => {},
  refreshAgents: async () => {},
  loading: true,
});

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
  });
  const [loading, setLoading] = useState(true);

  console.log("authState", authState);

  // Fetch agents data for supervisor
  const fetchAgentsForSupervisor = async (userId: string) => {
    try {
      console.log("🔍 Fetching agents for supervisor:", userId);
      
      // TODO: Replace with your actual API endpoint
      // This is a placeholder - update with your real endpoint
      const response = await axios.get(`https://10.16.7.96:5050/api/users`, {
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.status === 200 && response.data) {
        console.log("📋 All users from API:", response.data);
        
        // Filter agents where supervisor_reference matches current user
        const agents = response.data.filter(
          (user: any) => 
            user.supervisor_reference === userId &&
            (user.role === 'Agent' || user.role === 'agent')
        );
        
        console.log("✅ Filtered agents for supervisor:", agents);
        return agents;
      }
      
      return [];
    } catch (error) {
      console.error("❌ Error fetching agents:", error);
      
      // Fallback: Try to construct agents from WebSocket extensions
      const wsExtensions = sessionStorage.getItem('supervisor_extensions');
      if (wsExtensions) {
        console.log("📡 Using fallback: WebSocket extensions");
        const extensions = JSON.parse(wsExtensions);
        
        // Create basic agent objects from extensions
        return extensions.map((ext: string) => ({
          user_id: `agent_${ext}`,
          firstname: 'Agent',
          lastname: ext,
          fullname: `Agent ${ext}`,
          extension: ext,
          status: 'unknown',
          supervisor_reference: userId,
          role: 'Agent'
        }));
      }
      
      return [];
    }
  };

  // Load auth state from sessionStorage on mount
  useEffect(() => {
    const loadAuthState = async () => {
      const stored = sessionStorage.getItem("loginDetails");
      if (stored) {
        const user = JSON.parse(stored);
        
        // If user is a supervisor and doesn't have agents, fetch them
        if (user.role === 'Supervisor' && (!user.agents || user.agents.length === 0)) {
          console.log("🔄 Supervisor detected without agents, fetching...");
          const agents = await fetchAgentsForSupervisor(user.user_id);
          user.agents = agents;
          
          // Update sessionStorage with agents
          sessionStorage.setItem("loginDetails", JSON.stringify(user));
        }
        
        setAuthState({
          user,
          isAuthenticated: true,
        });
      }
      setLoading(false);
    };

    loadAuthState();
  }, []);

  const login = async (user: User) => {
    console.log("🔐 Login called with user:", user);
    
    // If supervisor, fetch agents immediately
    if (user.role === 'Supervisor') {
      console.log("👔 User is supervisor, fetching agents...");
      const agents = await fetchAgentsForSupervisor(user.user_id);
      user.agents = agents;
      console.log("✅ Agents fetched and attached:", agents);
    }
    
    setAuthState({
      user,
      isAuthenticated: true,
    });
    sessionStorage.setItem("loginDetails", JSON.stringify(user));
  };

  const logout = () => {
    setAuthState({
      user: null,
      isAuthenticated: false,
    });
    sessionStorage.removeItem("loginDetails");
    sessionStorage.removeItem("supervisor_extensions");
  };

  const updateUserStatus = (newStatus: string) => {
    if (authState.user) {
      const updatedUser = { ...authState.user, status: newStatus };
      setAuthState((prev) => ({
        ...prev,
        user: updatedUser,
      }));
      sessionStorage.setItem('loginDetails', JSON.stringify(updatedUser));
    }
  };

  // Manual refresh function for agents
  const refreshAgents = async () => {
    if (authState.user && authState.user.role === 'Supervisor') {
      console.log("🔄 Manually refreshing agents...");
      const agents = await fetchAgentsForSupervisor(authState.user.user_id);
      
      const updatedUser = { ...authState.user, agents };
      setAuthState((prev) => ({
        ...prev,
        user: updatedUser,
      }));
      sessionStorage.setItem('loginDetails', JSON.stringify(updatedUser));
    }
  };

  return (
    <AuthContext.Provider value={{ authState, login, logout, loading, updateUserStatus, refreshAgents }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);