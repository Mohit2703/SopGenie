'use client';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Bot, 
  Play, 
  RefreshCw, 
  CheckCircle, 
  AlertCircle, 
  Share2,
  MessageCircle,
  Loader2,
  XCircle,
  Clock
} from 'lucide-react';
import api from '@/lib/api';

export default function VectorDBManager({ moduleId, moduleName, projectId, isAdmin }) {
  const [showShareLink, setShowShareLink] = useState(false);
  const [copied, setCopied] = useState(false);
  const queryClient = useQueryClient();

  // Fetch vector store status
  const { data: vectorStore, isLoading: storeLoading } = useQuery({
    queryKey: ['vectordb-store', moduleId],
    queryFn: async () => {
      try {
        const response = await api.callAPI('get', `/vectordb/stores/module/${moduleId}/`);
        return response;
      } catch (error) {
        if (error.response?.status === 404) {
          return null;
        }
        throw error;
      }
    },
    refetchInterval: (data) => {
      if (data?.status === 'indexing') {
        return 3000;
      }
      return false;
    }
  });

  // Fetch all tasks for this module (both pending and processing)
  const { data: allTasks = [] } = useQuery({
    queryKey: ['vectordb-tasks', moduleId],
    queryFn: async () => {
      try {
        const response = await api.callAPI('get', `/vectordb/tasks/?module_id=${moduleId}`);
        // Handle different response structures
        if (Array.isArray(response)) {
          return response;
        }
        if (response.results && Array.isArray(response.results)) {
          return response.results;
        }
        if (response.data && Array.isArray(response.data)) {
          return response.data;
        }
        return [];
      } catch (error) {
        console.error('Error fetching tasks:', error);
        return [];
      }
    },
    refetchInterval: (data) => {
      // Safely check if data is an array and has active tasks
      if (Array.isArray(data) && data.length > 0) {
        const hasActiveTasks = data.some(task => 
          task?.status === 'pending' || task?.status === 'processing'
        );
        if (hasActiveTasks) {
          return 3000;
        }
      }
      return false;
    }
  });

  // Get the most recent active task (either pending or processing)
  const activeTask = Array.isArray(allTasks) 
    ? allTasks.find(task => 
        task?.status === 'pending' || task?.status === 'processing'
      ) 
    : null;

  // Fetch detailed task status if there's an active task
  const { data: taskStatus } = useQuery({
    queryKey: ['task-status', activeTask?.task_id],
    queryFn: async () => {
      if (!activeTask?.task_id) return null;
      try {
        return await api.callAPI('get', `/vectordb/tasks/status/${activeTask.task_id}/`);
      } catch (error) {
        console.error('Error fetching task status:', error);
        return null;
      }
    },
    enabled: !!activeTask?.task_id,
    refetchInterval: (data) => {
      if (data?.is_running || data?.status === 'pending') {
        return 3000;
      }
      return false;
    }
  });

  // Create vector DB mutation
  const createVectorDB = useMutation({
    mutationFn: async (forceRecreate = false) => {
      return await api.callAPI('post', '/vectordb/create/', {
        module_id: parseInt(moduleId),
        force_recreate: forceRecreate
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['vectordb-store', moduleId]);
      queryClient.invalidateQueries(['vectordb-tasks', moduleId]);
    }
  });

  const handleCreateVectorDB = (forceRecreate = false) => {
    createVectorDB.mutate(forceRecreate);
  };

  const getChatUrl = () => {
    return `${window.location.origin}/projects/${projectId}/modules/${moduleId}/chat/`;
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(getChatUrl());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Determine current state
  const isPending = activeTask?.status === 'pending' || taskStatus?.status === 'pending';
  const isProcessing = 
    vectorStore?.status === 'indexing' || 
    activeTask?.status === 'processing' ||
    taskStatus?.is_running ||
    createVectorDB.isPending;
  
  const isReady = vectorStore?.status === 'ready';
  const hasFailed = 
    vectorStore?.status === 'error' || 
    activeTask?.status === 'failed' ||
    taskStatus?.status === 'failed';
  
  const noVectorStore = vectorStore?.status === 'no_vector_store' && !activeTask && !createVectorDB.isPending;

  console.log('vectorStore: ', vectorStore);
  console.log('activeTask: ', !activeTask);
  console.log('createVectorDB: ', createVectorDB);
  console.log('hasFailed: ', hasFailed);


  // Get status badge
  const getStatusBadge = () => {
    if (isPending) {
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">
          <Clock size={16} className="mr-1" />
          Pending
        </span>
      );
    }
    
    if (isProcessing) {
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
          <Loader2 size={16} className="mr-1 animate-spin" />
          Processing
        </span>
      );
    }
    
    if (isReady) {
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
          <CheckCircle size={16} className="mr-1" />
          Ready
        </span>
      );
    }
    
    if (hasFailed) {
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
          <XCircle size={16} className="mr-1" />
          Failed
        </span>
      );
    }
    
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
        <AlertCircle size={16} className="mr-1" />
        Not Created
      </span>
    );
  };

  if (storeLoading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md border-2 border-blue-100">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="animate-spin text-blue-500" size={32} />
        </div>
      </div>
    );
  }


  return (
    <div className="bg-white p-6 rounded-lg shadow-md border-2 border-blue-100">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Bot className="text-blue-500" size={24} />
          <h3 className="text-lg font-semibold text-slate-800">AI Assistant (RAG)</h3>
        </div>
        {getStatusBadge()}
      </div>

      <p className="text-slate-600 mb-4 text-sm">
        {isReady 
          ? 'AI-powered question answering is ready for this module.' 
          : 'Create a vector database to enable AI-powered question answering.'}
      </p>

      {/* State 0: Pending - Show Waiting Status */}
      {isPending && (
        <div className="mb-4 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
          <div className="flex items-center mb-3">
            <Clock className="text-yellow-600 mr-2" size={20} />
            <span className="font-medium text-yellow-900">Task Queued</span>
          </div>
          
          <p className="text-sm text-yellow-700 mb-3">
            Your vector database creation task has been queued and will start processing soon.
          </p>

          <div className="flex items-center space-x-2 text-xs text-yellow-700">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-yellow-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-2 h-2 bg-yellow-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-2 h-2 bg-yellow-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
            <span>Waiting for worker...</span>
          </div>

          {activeTask && (
            <div className="mt-3 pt-3 border-t border-yellow-200">
              <div className="text-xs text-yellow-700">
                <div><span className="font-medium">Task ID:</span> {activeTask.task_id}</div>
                <div><span className="font-medium">Created:</span> {new Date(activeTask.created_at).toLocaleString()}</div>
                <div><span className="font-medium">Total Documents:</span> {activeTask.total_documents || 0}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* State 1: Processing - Show Progress */}
      {isProcessing && !isPending && (taskStatus || activeTask) && (
        <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <div className="flex items-center justify-between mb-3">
            <span className="font-medium text-blue-900 text-sm">
              {taskStatus?.current_step || 'Processing documents...'}
            </span>
            <span className="text-blue-700 font-semibold">
              {taskStatus?.progress_percentage || activeTask?.progress_percentage || 0}%
            </span>
          </div>
          
          <div className="w-full bg-blue-200 rounded-full h-2.5 mb-3">
            <div 
              className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
              style={{ 
                width: `${taskStatus?.progress_percentage || activeTask?.progress_percentage || 0}%` 
              }}
            />
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs text-blue-700">
            <div>
              <span className="font-medium">Total Documents:</span>
              <span className="ml-1">{taskStatus?.total_documents || activeTask?.total_documents || 0}</span>
            </div>
            <div>
              <span className="font-medium">Processed:</span>
              <span className="ml-1">{taskStatus?.processed_documents || activeTask?.processed_documents || 0}</span>
            </div>
            <div>
              <span className="font-medium">Successful:</span>
              <span className="ml-1 text-green-600">{taskStatus?.successful_documents || activeTask?.successful_documents || 0}</span>
            </div>
            <div>
              <span className="font-medium">Failed:</span>
              <span className="ml-1 text-red-600">{taskStatus?.failed_documents || activeTask?.failed_documents || 0}</span>
            </div>
          </div>

          {(taskStatus?.current_document || activeTask?.current_document) && (
            <div className="mt-3 pt-3 border-t border-blue-200">
              <div className="text-xs text-blue-700">
                <span className="font-medium">Current:</span>
                <span className="ml-1 truncate block">{taskStatus?.current_document || activeTask?.current_document}</span>
              </div>
            </div>
          )}

          <div className="mt-3 flex items-center text-xs text-blue-600">
            <Loader2 size={14} className="animate-spin mr-1" />
            <span>This may take a few minutes. You can safely leave this page.</span>
          </div>
        </div>
      )}

      {/* State 2: Ready - Show Statistics and Actions */}
      {isReady && vectorStore && !isPending && !isProcessing && (
        <div className="space-y-4">
          <div className="p-4 bg-green-50 rounded-lg border border-green-200">
            <div className="flex items-center mb-3">
              <CheckCircle className="text-green-600 mr-2" size={20} />
              <span className="font-medium text-green-900">Vector Database Ready!</span>
            </div>
            
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="bg-white p-3 rounded">
                <span className="text-gray-600 block text-xs">Documents</span>
                <span className="text-lg font-bold text-green-700">{vectorStore.document_count || 0}</span>
              </div>
              <div className="bg-white p-3 rounded">
                <span className="text-gray-600 block text-xs">Chunks</span>
                <span className="text-lg font-bold text-green-700">{vectorStore.total_chunks || 0}</span>
              </div>
              <div className="bg-white p-3 rounded col-span-2">
                <span className="text-gray-600 block text-xs">Embedding Model</span>
                <span className="text-sm font-medium text-gray-800">{vectorStore.embedding_model}</span>
              </div>
              {vectorStore.last_indexed_at && (
                <div className="bg-white p-3 rounded col-span-2">
                  <span className="text-gray-600 block text-xs">Last Indexed</span>
                  <span className="text-sm font-medium text-gray-800">
                    {new Date(vectorStore.last_indexed_at).toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons for Ready State */}
          <div className="space-y-2">
            <a
              href={`/projects/${projectId}/modules/${moduleId}/chat/`}
              className="w-full bg-blue-500 hover:bg-blue-600 text-white px-4 py-3 rounded-lg flex items-center justify-center space-x-2 transition-colors font-medium"
            >
              <MessageCircle size={20} />
              <span>Open Chat Interface</span>
            </a>

            <button
              onClick={() => setShowShareLink(!showShareLink)}
              className="w-full bg-white border-2 border-blue-500 text-blue-600 hover:bg-blue-50 px-4 py-3 rounded-lg flex items-center justify-center space-x-2 transition-colors font-medium"
            >
              <Share2 size={20} />
              <span>Share Chat Link</span>
            </button>

            {isAdmin && (
              <button
                onClick={() => handleCreateVectorDB(true)}
                disabled={createVectorDB.isPending}
                className="w-full bg-white border-2 border-orange-500 text-orange-600 hover:bg-orange-50 px-4 py-3 rounded-lg flex items-center justify-center space-x-2 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw size={20} className={createVectorDB.isPending ? 'animate-spin' : ''} />
                <span>{createVectorDB.isPending ? 'Recreating...' : 'Recreate Vector DB'}</span>
              </button>
            )}
          </div>

          {/* Share Link Panel */}
          {showShareLink && (
            <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-700 font-medium mb-2">Share this chat link:</p>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={getChatUrl()}
                  readOnly
                  className="flex-1 px-3 py-2 border border-gray-300 rounded text-sm bg-white font-mono"
                  onClick={(e) => e.target.select()}
                />
                <button
                  onClick={copyToClipboard}
                  className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm font-medium whitespace-nowrap"
                >
                  {copied ? '✓ Copied!' : 'Copy'}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Anyone with this link can chat with the AI about documents in this module.
              </p>
            </div>
          )}
        </div>
      )}

      {/* State 3: Failed - Show Error and Retry */}
      {hasFailed && !isProcessing && !isPending && (
        <div className="space-y-4">
          <div className="p-4 bg-red-50 rounded-lg border border-red-200">
            <div className="flex items-center mb-2">
              <XCircle className="text-red-600 mr-2" size={20} />
              <span className="font-medium text-red-900">Creation Failed</span>
            </div>
            <p className="text-sm text-red-700">
              {taskStatus?.error_message || activeTask?.error_message || 'An error occurred while creating the vector database.'}
            </p>
          </div>

          {isAdmin && (
            <button
              onClick={() => handleCreateVectorDB(true)}
              disabled={createVectorDB.isPending}
              className="w-full bg-red-500 hover:bg-red-600 text-white px-4 py-3 rounded-lg flex items-center justify-center space-x-2 transition-colors font-medium disabled:opacity-50"
            >
              <RefreshCw size={20} className={createVectorDB.isPending ? 'animate-spin' : ''} />
              <span>{createVectorDB.isPending ? 'Retrying...' : 'Retry Creation'}</span>
            </button>
          )}
        </div>
      )}

      {/* State 4: No Vector Store - Show Create Button */}
      {noVectorStore && !hasFailed && (
        <div className="space-y-4">
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-sm text-blue-800">
              <strong>What is a Vector Database?</strong>
            </p>
            <p className="text-xs text-blue-700 mt-2">
              A vector database converts your documents into searchable embeddings, enabling AI-powered semantic search and question answering.
            </p>
          </div>

          {isAdmin && (
            <button
              onClick={() => handleCreateVectorDB(false)}
              disabled={createVectorDB.isPending}
              className="w-full bg-blue-500 hover:bg-blue-600 text-white px-4 py-3 rounded-lg flex items-center justify-center space-x-2 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {createVectorDB.isPending ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  <span>Creating Vector Database...</span>
                </>
              ) : (
                <>
                  <Play size={20} />
                  <span>Create Vector Database</span>
                </>
              )}
            </button>
          )}

          {vectorStore?.document_count === 0 && (
            <p className="text-xs text-amber-600 text-center">
              ⚠️ This module has no documents. Upload documents before creating the vector database.
            </p>
          )}
        </div>
      )}

      {/* Error Display for Mutations */}
      {createVectorDB.isError && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700 font-medium">Failed to create vector database</p>
          <p className="text-xs text-red-600 mt-1">
            {createVectorDB.error?.response?.data?.error || 'Please try again or contact support if the issue persists.'}
          </p>
        </div>
      )}
    </div>
  );
}
