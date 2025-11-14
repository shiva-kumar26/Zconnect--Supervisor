import React from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Mic } from "lucide-react";
import {
  User,
  Bell,
  Settings,
  Home,
  Calendar,
  MessageSquare,
  Mail,
  Phone,
  GitBranch,
  LogOut,
  Activity,
  BarChart2
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface AdminSidebarProps {
  isOpen: boolean;
}

const AdminSidebar: React.FC<AdminSidebarProps> = ({ isOpen }) => {
  const { logout, authState } = useAuth();
  const user = authState.user;
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  let menuItems: { path: string; icon: any; label: string }[] = [];

  if (user?.role === 'Admin') {
    menuItems = [
      { path: '/dashboard', icon: Home, label: 'Dashboard' },
      { path: '/user-management', icon: User, label: 'User Management' },
      { path: '/queues', icon: Calendar, label: 'Queues' },
      { path: '/chat-templates', icon: MessageSquare, label: 'Chat Templates' },
      { path: '/email-templates', icon: Mail, label: 'Email Templates' },
      { path: '/dialplan', icon: Phone, label: 'Dialplan' },
      { path: '/ivr-flow', icon: GitBranch, label: 'IVR Flow' },
    ];
  } else if (user?.role === 'Supervisor') {
    menuItems = [
      { path: '/supervisor-dashboard', icon: Home, label: 'Home' },
      { path: '/my-agents', icon: User, label: 'My Agents' },
      { path: '/realtime-reports', icon: Activity, label: 'Realtime Reports' },
      { path: '/historical-reports', icon: BarChart2, label: 'Historical Reports' },
      { path: '/recordings', icon: Mic, label: 'Recordings' },
    ];
  } else if (user?.role === 'Agent') {
    menuItems = [
      { path: '/dashboard', icon: Home, label: 'Home' },
    ];
  }

  return (
    <aside
      className={`fixed left-0 top-0 h-screen ${
        isOpen ? 'w-64' : 'w-20'
      } bg-white border-r border-gray-200 z-40 transition-all duration-300`}
    >
      <div className="w-full flex items-center justify-center py-2">
        <img
          src="./Zeniusitservices.png"
          alt="logo"
          className="w-24 h-14 object-contain"
        />
      </div>

      <nav className="flex flex-col h-full">
        <div className="overflow-y-auto flex-1">
          {/* Admin menu */}
          {user?.role === 'Admin' && (
            <ul className="space-y-2 px-2">
              {menuItems.map((item) => (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    end={item.path === '/dashboard'}
                    className={({ isActive }) => {
                      let active = isActive;
                      if (item.path === '/user-management') {
                        active =
                          location.pathname === '/user-management' ||
                          location.pathname.startsWith('/user-details') ||
                          location.pathname === '/user-creation';
                      } else if (item.path === '/ivr-flow') {
                        active = location.pathname.startsWith('/ivr-flow');
                      }
                      return `flex items-center ${
                        isOpen ? 'space-x-3 px-4' : 'justify-center px-2'
                      } py-3 rounded-lg transition-all duration-200 ${
                        active
                          ? 'bg-blue-50 text-blue-600 shadow-lg border border-blue-200'
                          : 'text-gray-600 hover:bg-gray-50 hover:text-blue-600'
                      }`;
                    }}
                    title={!isOpen ? item.label : undefined}
                  >
                    <item.icon className="w-5 h-5 text-blue-600 flex-shrink-0" />
                    {isOpen && <span className="font-medium">{item.label}</span>}
                  </NavLink>
                </li>
              ))}
            </ul>
          )}

          {/* Supervisor menu */}
          {user?.role === 'Supervisor' && (
            <ul className="space-y-2 px-4">
              {menuItems.map((item) => (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    className={({ isActive }) =>
                      `flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                        isActive
                          ? 'bg-blue-50 shadow-lg border border-blue-200'
                          : 'hover:bg-gray-50'
                      }`
                    }
                  >
                    <item.icon className="w-5 h-5 text-blue-600" />
                    {isOpen && (
                      <span className="font-medium text-gray-600 hover:text-blue-600">
                        {item.label}
                      </span>
                    )}
                  </NavLink>
                </li>
              ))}

              {/* Notifications for Supervisor */}
              <li>
                <NavLink
                  to="/notifications"
                  className={({ isActive }) =>
                    `flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                      isActive
                        ? 'bg-blue-50 shadow-lg border border-blue-200'
                        : 'hover:bg-gray-50'
                    }`
                  }
                  title={!isOpen ? 'Notifications' : undefined}
                >
                  <Bell className="w-5 h-5 text-blue-600" />
                  {isOpen && (
                    <span className="font-medium text-gray-600 hover:text-blue-600">
                      Notifications
                    </span>
                  )}
                </NavLink>
              </li>
            </ul>
          )}

          {/* Agent menu */}
          {user?.role === 'Agent' && (
            <ul className="space-y-2 px-4">
              {menuItems.map((item) => (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    className={({ isActive }) =>
                      `flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                        isActive
                          ? 'bg-blue-50 text-blue-600 shadow-lg border border-blue-200'
                          : 'text-gray-600 hover:bg-gray-50 hover:text-blue-600'
                      }`
                    }
                  >
                    <item.icon className="w-5 h-5 text-blue-600" />
                    {isOpen && <span className="font-medium">{item.label}</span>}
                  </NavLink>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Footer Section */}
        <div className="border-t border-gray-200 p-4 space-y-2">
          {/* Notifications & Settings only for Admin */}
          {user?.role === 'Admin' && isOpen && (
            <>
              <NavLink
                to="/notifications"
                className={({ isActive }) =>
                  `flex items-center ${
                    isOpen ? 'space-x-3 px-4' : 'justify-center px-2'
                  } py-3 rounded-lg transition-all duration-200 ${
                    isActive
                      ? 'bg-blue-50 text-blue-600 shadow-lg border border-blue-200'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-blue-600'
                  }`
                }
                title={!isOpen ? 'Notifications' : undefined}
              >
                <Bell className="w-5 h-5 text-blue-600 flex-shrink-0" />
                {isOpen && <span className="font-medium">Notifications</span>}
              </NavLink>

              <NavLink
                to="/settings"
                className={({ isActive }) =>
                  `flex items-center ${
                    isOpen ? 'space-x-3 px-4' : 'justify-center px-2'
                  } py-3 rounded-lg transition-all duration-200 ${
                    isActive
                      ? 'bg-blue-50 text-blue-600 shadow-lg border border-blue-200'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-blue-600'
                  }`
                }
                title={!isOpen ? 'Settings' : undefined}
              >
                <Settings className="w-5 h-5 text-blue-600 flex-shrink-0" />
                {isOpen && <span className="font-medium">Settings</span>}
              </NavLink>
            </>
          )}

          {/* Logout for all roles */}
          <Button
            onClick={handleLogout}
            variant="ghost"
            className={`w-full flex items-center ${
              isOpen ? 'justify-start space-x-3 px-4' : 'justify-center px-2'
            } py-3 rounded-lg transition-all duration-200 text-gray-600 hover:bg-gray-50 hover:text-blue-600`}
            title={!isOpen ? 'Logout' : undefined}
          >
            <LogOut className="w-5 h-5 text-blue-600 flex-shrink-0" />
            {isOpen && <span className="font-medium">Logout</span>}
          </Button>
        </div>
      </nav>
    </aside>
  );
};

export default AdminSidebar;