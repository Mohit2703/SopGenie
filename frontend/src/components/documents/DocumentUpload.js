'use client';
import { useState } from 'react';
import { Upload, File, X, CheckCircle } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';

export default function DocumentUpload({ projectId, moduleId, onUploadSuccess }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});
  const [uploadStatus, setUploadStatus] = useState({});
  
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: async ({ file, index }) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', file.name);
      
      setUploadStatus(prev => ({ ...prev, [index]: 'uploading' }));
      
      // Use the callAPI method with 'upload' method
      const response = await api.callAPI(
        'upload', 
        `/modules/${moduleId}/documents/`, 
        formData,
        {}, // params
        null, // token (will use from localStorage)
        (progressEvent) => { // onUploadProgress
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setUploadProgress(prev => ({ ...prev, [index]: progress }));
        }
      );
      
      setUploadStatus(prev => ({ ...prev, [index]: 'success' }));
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', moduleId] });
      onUploadSuccess?.();
    },
    onError: (error, variables) => {
      setUploadStatus(prev => ({ ...prev, [variables.index]: 'error' }));
      console.error('Upload failed:', error);
    }
  });

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(prev => [...prev, ...selectedFiles]);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(prev => [...prev, ...droppedFiles]);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
    setUploadProgress(prev => {
      const newProgress = { ...prev };
      delete newProgress[index];
      return newProgress;
    });
    setUploadStatus(prev => {
      const newStatus = { ...prev };
      delete newStatus[index];
      return newStatus;
    });
  };

  const uploadDocuments = async () => {
    if (files.length === 0) return;

    setUploading(true);
    
    try {
      // Upload files one by one
      for (let i = 0; i < files.length; i++) {
        await uploadMutation.mutateAsync({ file: files[i], index: i });
      }
      
      // Clear files after successful upload
      setTimeout(() => {
        setFiles([]);
        setUploadProgress({});
        setUploadStatus({});
      }, 2000);
      
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="text-green-500" size={16} />;
      case 'error':
        return <X className="text-red-500" size={16} />;
      default:
        return null;
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'uploading':
        return 'Uploading...';
      case 'success':
        return 'Complete';
      case 'error':
        return 'Failed';
      default:
        return '';
    }
  };

  return (
    <div className="space-y-4">
      <div 
        className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-gray-400 transition-colors"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <Upload className="mx-auto text-gray-400 mb-3" size={32} />
        <p className="text-slate-600 mb-3">
          Drag and drop files here, or click to select
        </p>
        <p className="text-sm text-slate-500 mb-4">
          Supports: PDF, DOC, DOCX, TXT files (Max: 50MB)
        </p>
        <input
          type="file"
          multiple
          accept=".pdf,.doc,.docx,.txt"
          onChange={handleFileSelect}
          className="hidden"
          id="file-upload"
        />
        <label
          htmlFor="file-upload"
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg cursor-pointer inline-block"
        >
          Select Files
        </label>
      </div>

      {files.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-medium text-slate-800">Selected Files ({files.length})</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {files.map((file, index) => (
              <div key={index} className="flex items-center justify-between bg-white p-3 rounded border">
                <div className="flex items-center space-x-3 flex-1">
                  <File size={16} className="text-blue-500" />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium text-slate-800 truncate block">{file.name}</span>
                    <span className="text-xs text-slate-500">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3">
                  {uploadStatus[index] && (
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(uploadStatus[index])}
                      <span className="text-xs text-slate-600">
                        {getStatusText(uploadStatus[index])}
                      </span>
                    </div>
                  )}
                  
                  {uploadProgress[index] !== undefined && uploadStatus[index] === 'uploading' && (
                    <div className="flex items-center space-x-2">
                      <div className="w-16 bg-gray-200 rounded-full h-1.5">
                        <div
                          className="bg-blue-600 h-1.5 rounded-full transition-all"
                          style={{ width: `${uploadProgress[index]}%` }}
                        ></div>
                      </div>
                      <span className="text-xs text-slate-600">{uploadProgress[index]}%</span>
                    </div>
                  )}
                  
                  {!uploading && (
                    <button
                      onClick={() => removeFile(index)}
                      className="text-red-500 hover:text-red-700 p-1"
                    >
                      <X size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
          
          <button
            onClick={uploadDocuments}
            disabled={uploading || files.length === 0}
            className="w-full bg-green-500 hover:bg-green-600 text-white py-3 px-4 rounded-lg disabled:opacity-50 font-medium"
          >
            {uploading ? 'Uploading...' : `Upload ${files.length} Document${files.length > 1 ? 's' : ''}`}
          </button>
        </div>
      )}
    </div>
  );
}
