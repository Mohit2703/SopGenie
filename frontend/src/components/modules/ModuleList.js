'use client';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { Plus, Folder, FileText, Calendar, ChevronRight, X } from 'lucide-react';
import api from '@/lib/api';

// Create Module Modal
function CreateModuleModal({ projectId, onClose, onSubmit }) {
  const [formData, setFormData] = useState({ name: '', description: '' });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onSubmit({ ...formData, project_id: projectId });
      onClose();
    } catch (error) {
      console.error('Failed to create module:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-slate-800">Create New Module</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <X size={20} />
          </button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Module Name
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
              placeholder="Enter module name"
            />
          </div>
          
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
              placeholder="Enter module description"
            />
          </div>
          
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 text-slate-700 bg-gray-100 rounded-md hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Module Item Component
function ModuleItem({ module, projectId }) {
  const router = useRouter();
  
  const handleModuleClick = () => {
    router.push(`/projects/${projectId}/modules/${module.id}`);
  };

  return (
    <div 
      className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer"
      onClick={handleModuleClick}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Folder className="text-blue-500" size={24} />
          <div>
            <h3 className="text-lg font-semibold text-slate-800">{module.name}</h3>
            {module.description && (
              <p className="text-sm text-slate-600 mt-1">{module.description}</p>
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="text-right text-sm text-slate-500">
            <div className="flex items-center space-x-1">
              <FileText size={16} />
              <span>{module.documents_count || 0} docs</span>
            </div>
            <div className="flex items-center space-x-1 mt-1">
              <Calendar size={16} />
              <span>{new Date(module.created_at).toLocaleDateString()}</span>
            </div>
          </div>
          <ChevronRight className="text-gray-400" size={20} />
        </div>
      </div>
    </div>
  );
}

// Main Module List Component
export default function ModuleList({ projectId }) {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const queryClient = useQueryClient();

  const { data: modules = [], isLoading } = useQuery({
    queryKey: ['modules', projectId],
    queryFn: async () => {
      const response = await api.callAPI('get', `/projects/${projectId}/modules/`);
      return response;
    }
  });

  const createModuleMutation = useMutation({
    mutationFn: (moduleData) => api.post('/modules/', moduleData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modules', projectId] });
      setShowCreateForm(false);
    }
  });

  const handleCreateModule = (moduleData) => {
    createModuleMutation.mutate(moduleData);
  };

  if (isLoading) {
    return <div className="flex justify-center p-8 text-slate-600">Loading modules...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-slate-800">Modules</h2>
        <button
          onClick={() => setShowCreateForm(true)}
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2"
        >
          <Plus size={20} />
          New Module
        </button>
      </div>

      {modules.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-gray-300">
          <Folder className="mx-auto text-gray-400 mb-4" size={48} />
          <h3 className="text-lg font-medium text-slate-800 mb-2">No modules yet</h3>
          <p className="text-slate-600 mb-4">
            Create your first module to organize your SOP documents
          </p>
          <button
            onClick={() => setShowCreateForm(true)}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg"
          >
            Create Module
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {modules.map((module) => (
            <ModuleItem
              key={module.id}
              module={module}
              projectId={projectId}
            />
          ))}
        </div>
      )}

      {showCreateForm && (
        <CreateModuleModal
          projectId={projectId}
          onClose={() => setShowCreateForm(false)}
          onSubmit={handleCreateModule}
        />
      )}
    </div>
  );
}
