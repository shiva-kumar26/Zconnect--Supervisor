import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { User, Search, ChevronUp, ChevronDown } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useWebSocketEvent } from '@/contexts/WebSocketContext';
import axios from 'axios';

const SupervisorDashboard = () => {
  const { authState } = useAuth();
  const { teamMembers, setTeamMembers } = useWebSocketEvent();
  const user = authState.user;
  const [loading, setLoading] = useState(true);
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // Fetch agent status from API
  const getAgentStatus = async (stationId: string) => {
    const requestBody = { agent: stationId };
    try {
      const response = await axios.post('https://10.16.7.96:5050/Get-Agent-Status', requestBody, {
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.status === 200) {
        return response.data.status;
      }
    } catch (error) {
      console.error(`Failed to fetch status for ${stationId}:`, error);
      return null;
    }
  };

  // Initialize agents from user data
  useEffect(() => {
    const initializeAgents = async () => {
      if (!user) {
        console.log("❌ No user found");
        setLoading(false);
        return;
      }

      console.log("🔵 User object:", user);

      // Check if agents exist in user object
      if (user.agents && Array.isArray(user.agents) && user.agents.length > 0) {
        console.log("✅ Found agents in user object:", user.agents);
        
        const filteredAgents = user.agents.filter(
          agent => agent?.supervisor_reference === user?.user_id
        );
        
        console.log("🔵 Filtered agents for supervisor:", filteredAgents);

        // Fetch current status for each agent
        const mappedAgents = await Promise.all(
          filteredAgents.map(async (agent) => {
            const currentStatus = await getAgentStatus(agent.extension || '');
            const status = currentStatus || agent.status || 'unknown';
            
            return {
              id: agent.user_id,
              fullname: agent.fullname || `${agent.firstname} ${agent.lastname}`,
              extension: agent.extension,
              status: status,
            };
          })
        );
        
        console.log("🔵 Setting teamMembers:", mappedAgents);
        setTeamMembers(mappedAgents);
      } else {
        console.warn("⚠️ user.agents is empty or not an array");
        console.log("📋 Full user object structure:", JSON.stringify(user, null, 2));
        
        // TEMPORARY WORKAROUND: Use hardcoded extensions from supervisor_connected message
        // Extensions monitoring: ['1031', '1033', '1041', '1032', '1029']
        let extensions = ['1031', '1033', '1041', '1032', '1029'];
        
        // Try to get from WebSocket first
        const wsExtensions = sessionStorage.getItem('supervisor_extensions');
        if (wsExtensions) {
          extensions = JSON.parse(wsExtensions);
          console.log("📡 Using extensions from WebSocket:", extensions);
        } else {
          console.log("📌 Using hardcoded extensions:", extensions);
        }
        
        const mockAgents = await Promise.all(
          extensions.map(async (ext: string) => {
            const currentStatus = await getAgentStatus(ext);
            return {
              id: `agent_${ext}`,
              fullname: `Agent ${ext}`,
              extension: ext,
              status: currentStatus || 'Logged Out',
            };
          })
        );
        
        console.log("✅ Created agents from extensions:", mockAgents);
        setTeamMembers(mockAgents);
      }
      
      setLoading(false);
    };

    initializeAgents();
  }, [user?.user_id, setTeamMembers]);

  // Log teamMembers changes
  useEffect(() => {
    console.log("📊 TeamMembers updated, count:", teamMembers.length, teamMembers);
  }, [teamMembers]);

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'available':
        return 'bg-green-100 text-green-800';
      case 'logged out':
        return 'bg-yellow-100 text-yellow-800';
      case 'on break':
        return 'bg-red-100 text-red-800';
      case 'busy':
      case 'on call':
        return 'bg-red-100 text-red-800';
      case 'waiting':
        return 'bg-blue-100 text-blue-800';
      case 'available (on demand)':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getAvatarGradient = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'available':
        return 'linear-gradient(to right, #10b981, #34d399)';
      case 'logged out':
        return 'linear-gradient(to right, #f59e0b, #facc15)';
      case 'on break':
      case 'busy':
      case 'on call':
        return 'linear-gradient(to right, #ef4444, #f87171)';
      case 'waiting':
        return 'linear-gradient(to right, #3b82f6, #60a5fa)';
      case 'available (on demand)':
        return 'linear-gradient(to right, #6b7280, #9ca3af)';
      default:
        return 'linear-gradient(to right, #6b7280, #9ca3af)';
    }
  };

  const toggleAgentsList = () => {
    setIsOpen(!isOpen);
  };

  const filteredAgents = teamMembers?.filter(agent => 
    agent.fullname?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    agent.extension?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-lg text-gray-600">Loading supervisor dashboard...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6 h-[calc(100vh-64px)]">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-gradient-to-r from-blue-500 to-cyan-600 text-white">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <User className="w-5 h-5" />
              <span>Total Agents</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{teamMembers?.length || 0}</div>
            <p className="text-sm opacity-90">Under your supervision</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-r from-green-500 to-emerald-600 text-white">
          <CardHeader>
            <CardTitle>Available Agents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {teamMembers?.filter(a => a.status?.toLowerCase() === 'available')?.length || 0}
            </div>
            <p className="text-sm opacity-90">Ready to take calls</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-r from-red-500 to-pink-600 text-white">
          <CardHeader>
            <CardTitle>Active Calls</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {teamMembers?.filter(a => a.status?.toLowerCase() === 'busy' || a.status?.toLowerCase() === 'on call')?.length || 0}
            </div>
            <p className="text-sm opacity-90">Currently in progress</p>
          </CardContent>
        </Card>
      </div>
      
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Agent Status Overview</CardTitle>
            <div className="flex items-center space-x-4">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500" />
                <Input
                  placeholder="Search agents..."
                  className="pl-10 w-64"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleAgentsList}
                className="p-1"
              >
                {isOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isOpen && (
            <>
              {filteredAgents?.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-lg font-medium mb-2">
                    {searchTerm ? 'No agents match your search' : 'No agents found'}
                  </div>
                  {!searchTerm && (
                    <div className="text-sm text-gray-400 mt-2">
                      Please check that user.agents is populated in your AuthContext
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-4">
                  {filteredAgents?.map((agent) => (
                    <div key={agent.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-4">
                        <div
                          className="w-10 h-10 rounded-full flex items-center justify-center text-white font-medium"
                          style={{
                            background: getAvatarGradient(agent?.status),
                          }}
                        >
                          {agent?.fullname?.split(' ').map(n => n[0]).join('').toUpperCase()}
                        </div>
                        <div>
                          <div className="font-medium text-gray-900">{agent?.fullname}</div>
                          <div className="text-sm text-gray-500">Station: {agent?.extension || 'N/A'}</div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        <Badge className={getStatusColor(agent?.status)}>
                          {agent?.status}
                        </Badge>
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-xs"
                        >
                          Change Status
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default SupervisorDashboard;