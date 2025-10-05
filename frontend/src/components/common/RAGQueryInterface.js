'use client';
import { useState } from 'react';
import { Send, MessageCircle, BookOpen } from 'lucide-react';
import api from '@/lib/api';

export default function RAGQueryInterface({ projectId }) {
  const [query, setQuery] = useState('');
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userMessage = { role: 'user', content: query, timestamp: Date.now() };
    setConversation(prev => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await api.post('/vectordb/query/', {
        query: query,
        project_id: projectId,
        max_results: 5
      });

      const aiMessage = {
        role: 'assistant',
        content: response.data.answer,
        sources: response.data.sources,
        timestamp: Date.now()
      };
      
      setConversation(prev => [...prev, aiMessage]);
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your query. Please try again.',
        timestamp: Date.now(),
        error: true
      };
      setConversation(prev => [...prev, errorMessage]);
    } finally {
      setQuery('');
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md h-96 flex flex-col">
      <div className="p-4 border-b bg-gray-50 rounded-t-lg">
        <h3 className="font-semibold flex items-center gap-2">
          <MessageCircle size={20} />
          Ask about your SOPs
        </h3>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {conversation.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <BookOpen size={48} className="mx-auto mb-4 text-gray-300" />
            <p>Start asking questions about your Standard Operating Procedures</p>
          </div>
        ) : (
          conversation.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : message.error
                    ? 'bg-red-100 text-red-800 border border-red-200'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                
                {message.sources && message.sources.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-200">
                    <p className="text-xs text-gray-600 mb-1">Sources:</p>
                    {message.sources.map((source, idx) => (
                      <div key={idx} className="text-xs text-gray-500">
                        • {source.document_name} (Score: {source.similarity_score?.toFixed(3)})
                      </div>
                    ))}
                  </div>
                )}
                
                <div className="text-xs text-gray-500 mt-1">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))
        )}
        
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 px-4 py-2 rounded-lg">
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                <span className="text-sm text-gray-600">Searching knowledge base...</span>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about procedures, policies, or guidelines..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={18} />
          </button>
        </div>
      </form>
    </div>
  );
}
