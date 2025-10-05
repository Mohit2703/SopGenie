'use client';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { File, Download, Trash2, Calendar, User, FileText, Search } from 'lucide-react';
import api from '@/lib/api';

export default function DocumentList({ moduleId }) {
  const [searchTerm, setSearchTerm] = useState('');
  const queryClient = useQueryClient();

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['documents', moduleId],
    queryFn: async () => {
      const response = await api.callAPI('get', `/modules/${moduleId}/documents/`);
      console.log("Fetched documents: ", response);
      return response;
    },
    enabled: !!moduleId
  });

  const deleteDocumentMutation = useMutation({
    mutationFn: (documentId) => api.callAPI('delete', `/documents/${documentId}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', moduleId] });
    }
  });

  const handleDeleteDocument = (documentId) => {
    if (window.confirm('Are you sure you want to delete this document?')) {
      deleteDocumentMutation.mutate(documentId);
    }
  };

  const handleDownloadDocument = async (documentId, filename) => {
    try {
      // Create direct download URL
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
      const downloadUrl = `${API_BASE_URL}/documents/${documentId}/download/`;
      const token = localStorage.getItem('Token');
      
      // Use fetch to download with proper headers
      const response = await fetch(downloadUrl, {
        method: 'GET',
        headers: {
          'Authorization': `Token ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Get the blob from response
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      
      // Create download link
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename || `document_${documentId}`);
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      link.remove();
      window.URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Download failed:', error);
      alert('Download failed. Please try again.');
    }
  };

  // Filter documents based on search term - FIXED
  const filteredDocuments = documents.filter(doc => {
    if (!searchTerm) return true;
    
    const searchLower = searchTerm.toLowerCase();
    return (
      doc.title?.toLowerCase().includes(searchLower) ||
      doc.description?.toLowerCase().includes(searchLower) ||
      doc.uploaded_by?.toLowerCase().includes(searchLower)
    );
  });

  if (isLoading) {
    return <div className="text-center py-4 text-slate-600">Loading documents...</div>;
  }

  return (
    <div className="space-y-4">
      {documents.length > 0 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="text"
            placeholder="Search documents..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
          />
        </div>
      )}

      {filteredDocuments.length === 0 ? (
        <div className="text-center py-8 text-slate-500">
          {documents.length === 0 ? (
            <>
              <FileText className="mx-auto mb-2 text-gray-400" size={32} />
              <p>No documents uploaded yet</p>
            </>
          ) : (
            <p>No documents match your search</p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filteredDocuments.map((document) => (
            <div
              key={document.id}
              className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <div className="flex items-center space-x-3 flex-1">
                <File className="text-blue-500 flex-shrink-0" size={20} />
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-slate-800 truncate">{document.title}</h4>
                  {document.description && (
                    <p className="text-sm text-slate-600 truncate">{document.description}</p>
                  )}
                  <div className="flex items-center space-x-4 text-xs text-slate-500 mt-1">
                    <span className="flex items-center space-x-1">
                      <Calendar size={12} />
                      <span>{new Date(document.uploaded_at).toLocaleDateString()}</span>
                    </span>
                    {document.file_size && (
                      <span>{(document.file_size / 1024 / 1024).toFixed(2)} MB</span>
                    )}
                    {document.uploaded_by_name && (
                      <span className="flex items-center space-x-1">
                        <User size={12} />
                        <span>{document.uploaded_by_name}</span>
                      </span>
                    )}
                    {document.file_type && (
                      <span className="bg-gray-200 px-2 py-1 rounded text-xs">
                        {document.file_type.replace('.', '').toUpperCase()}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2 ml-4">
                <button
                  onClick={() => handleDownloadDocument(document.id, document.title)}
                  className="p-2 text-blue-600 hover:text-blue-800 hover:bg-blue-100 rounded transition-colors"
                  title="Download"
                  disabled={!document.file}
                >
                  <Download size={16} />
                </button>
                <button
                  onClick={() => handleDeleteDocument(document.id)}
                  className="p-2 text-red-600 hover:text-red-800 hover:bg-red-100 rounded transition-colors"
                  title="Delete"
                  disabled={deleteDocumentMutation.isLoading}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Loading state for delete operation */}
      {deleteDocumentMutation.isLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-4 rounded-lg">
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600"></div>
              <span>Deleting document...</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
