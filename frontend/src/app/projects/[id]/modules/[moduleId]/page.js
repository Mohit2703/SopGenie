'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import DocumentUpload from '@/components/documents/DocumentUpload';
import DocumentList from '@/components/documents/DocumentList';
import RAGQueryInterface from '@/components/common/RAGQueryInterface';
import api from '@/lib/api';
import { Folder, ArrowLeft } from 'lucide-react';

export default function ModuleDetailPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const params = useParams();
  const router = useRouter();
  const { id: projectId, moduleId } = params;

  useEffect(() => {
    const token = localStorage.getItem('Token');
    if (token) {
      setIsAuthenticated(true);
    } else {
      router.push('/login');
    }
    setIsLoading(false);
  }, [router]);

  const { data: module, isLoading: moduleLoading } = useQuery({
    queryKey: ['module', moduleId],
    queryFn: async () => {
      const response = await api.callAPI('get', `/modules_details/${moduleId}/`);
      return response;
    },
    enabled: isAuthenticated
  });

  const { data: project } = useQuery({
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

  if (moduleLoading) {
    return <div className="flex justify-center items-center min-h-screen text-slate-600">Loading module...</div>;
  }

  if (!module) {
    return <div className="flex justify-center items-center min-h-screen text-slate-600">Module not found</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.push(`/projects/${projectId}`)}
                className="text-blue-600 hover:text-blue-800 flex items-center space-x-2"
              >
                <ArrowLeft size={16} />
                <span>Back to {project?.name || 'Project'}</span>
              </button>
              <div className="flex items-center space-x-2 text-slate-600">
                <span>/</span>
                <Folder size={16} className="text-blue-500" />
                <span className="text-slate-800 font-semibold">{module.name}</span>
              </div>
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
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Left Column - Module Info and Documents */}
          <div className="lg:col-span-2 space-y-8">
            {/* Module Overview */}
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h2 className="text-2xl font-bold mb-4 text-slate-800 flex items-center space-x-2">
                <Folder className="text-blue-500" size={24} />
                <span>{module.name}</span>
              </h2>
              {module.description && (
                <p className="text-slate-600 mb-6">{module.description}</p>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-blue-800">Created</h3>
                  <p className="text-blue-600">
                    {new Date(module.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-green-800">Documents</h3>
                  <p className="text-green-600">{module.documents_count || 0}</p>
                </div>
              </div>
            </div>

            {/* Document Upload Section */}
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold mb-4 text-slate-800">Upload Documents</h3>
              <DocumentUpload 
                projectId={projectId}
                moduleId={moduleId}
                onUploadSuccess={() => {
                  // The document list will automatically refresh via React Query
                }}
              />
            </div>

            {/* Document List Section */}
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold mb-4 text-slate-800">Documents</h3>
              <DocumentList moduleId={moduleId} />
            </div>
          </div>

          {/* Right Column - RAG Interface */}
          <div className="lg:col-span-1">
            <div className="sticky top-8">
              <RAGQueryInterface 
                projectId={projectId} 
                moduleId={moduleId}
                title={`Ask about ${module.name}`}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
