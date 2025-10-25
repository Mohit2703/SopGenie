'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import ModuleList from '@/components/modules/ModuleList';
import UserManagement from '@/components/projects/UserManagement';
import api from '@/lib/api';
import { Users } from 'lucide-react';

export default function ProjectDetailPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeTab, setActiveTab] = useState('modules'); // 'modules' or 'team'
  const params = useParams();
  const router = useRouter();
  const projectId = params.id;

  useEffect(() => {
    const token = localStorage.getItem('Token');
    if (token) {
      setIsAuthenticated(true);
    } else {
      router.push('/login');
    }
    setIsLoading(false);
  }, [router]);

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: async () => {
      const response = await api.callAPI('get', `/projects/${projectId}/`);
      return response;
    },
    enabled: isAuthenticated
  });

  const handleLogout = () => {
    localStorage.removeItem('Token');
    router.push('/');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (projectLoading) {
    return <div className="flex justify-center items-center min-h-screen text-slate-600">Loading project...</div>;
  }

  if (!project) {
    return <div className="flex justify-center items-center min-h-screen text-slate-600">Project not found</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.push('/dashboard')}
                className="text-blue-600 hover:text-blue-800"
              >
                ← Back to Dashboard
              </button>
              <h1 className="text-xl font-semibold text-slate-800">{project.name}</h1>
            </div>
            <button 
              onClick={handleLogout}
              className="text-red-600 hover:text-red-800"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* Project Overview */}
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-2xl font-bold mb-4 text-slate-800">Project Overview</h2>
            <p className="text-slate-600 mb-6">{project.description}</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <h3 className="font-semibold text-blue-800">Created</h3>
                <p className="text-blue-600">
                  {new Date(project.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <h3 className="font-semibold text-green-800">Modules</h3>
                <p className="text-green-600">{project.modules_count || 0}</p>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <h3 className="font-semibold text-purple-800">Status</h3>
                <p className="text-purple-600">Active</p>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="flex gap-8">
              <button
                onClick={() => setActiveTab('modules')}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition ${
                  activeTab === 'modules'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Modules
              </button>
              <button
                onClick={() => setActiveTab('team')}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition flex items-center gap-2 ${
                  activeTab === 'team'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Users className="h-4 w-4" />
                Team
              </button>
            </nav>
          </div>
          
          {/* Content */}
          {activeTab === 'modules' ? (
            <ModuleList projectId={projectId} />
          ) : (
            <UserManagement projectId={projectId} />
          )}
        </div>
      </div>
    </div>
  );
}
