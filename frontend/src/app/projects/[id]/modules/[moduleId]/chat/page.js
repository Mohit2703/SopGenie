"use client";

import { useState, useEffect, useRef, use } from "react";
import { 
  Send, Bot, User, Loader2, AlertCircle, ThumbsUp, ThumbsDown,
  Plus, MessageSquare, Trash2, Edit2, Menu, X, Clock
} from "lucide-react";
import api from '@/lib/api';

export default function ChatPage({ params }) {
  const unwrappedParams = use(params);
  const moduleId = unwrappedParams.moduleId;
  
  // State
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  
  const scrollAreaRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, [moduleId]);

  // Load session messages when session changes
  useEffect(() => {
    if (currentSession) {
      loadSessionHistory(currentSession.session_id);
    }
  }, [currentSession]);

  const loadSessions = async () => {
    setIsLoadingSessions(true);
    try {
      // Using your API: /vectordb/chat_session/module_id/
      const data = await api.callAPI('get', `/vectordb/chat_session/${moduleId}/`);
      
      setSessions(data || []);
      
      // Auto-select first session
      if (data && data.length > 0) {
        setCurrentSession(data[0]);
      }
    } catch (err) {
      console.error("Failed to load sessions:", err);
      setError("Failed to load chat sessions");
    } finally {
      setIsLoadingSessions(false);
    }
  };

  const loadSessionHistory = async (sessionId) => {
    try {
      // Using your API: /vectordb/chat_session/module_id/session_id/
      const data = await api.callAPI('get', `/vectordb/chat_session/${moduleId}/${sessionId}/`);
      
      // Transform chat_history to messages format
      const transformedMessages = [];
      
      if (data.chat_history && data.chat_history.length > 0) {
        data.chat_history.forEach((item, index) => {
          // Add question
          transformedMessages.push({
            id: `q-${index}`,
            role: "user",
            text: item.question,
            timestamp: new Date(item.asked_at),
          });
          
          // Add answer
          transformedMessages.push({
            id: `a-${index}`,
            role: "assistant",
            text: item.answer,
            timestamp: new Date(item.answered_at),
            processingTime: calculateProcessingTime(item.asked_at, item.answered_at),
          });
        });
      }
      
      setMessages(transformedMessages);
    } catch (err) {
      console.error("Failed to load session history:", err);
      setMessages([]);
    }
  };

  const calculateProcessingTime = (askedAt, answeredAt) => {
    const asked = new Date(askedAt);
    const answered = new Date(answeredAt);
    return (answered - asked) / 1000; // Convert to seconds
  };

  const createNewSession = async () => {
    // Just switch to no session - new session will be created on first message
    setCurrentSession(null);
    setMessages([]);
    inputRef.current?.focus();
  };

  const deleteSession = async (sessionId, e) => {
    e.stopPropagation();
    
    if (!confirm("Delete this chat?")) return;
    
    try {
      // Assuming you have delete endpoint: DELETE /vectordb/chat_session/module_id/session_id/
      await api.callAPI('post', `/vectordb/delete_session/${sessionId}/`);
      
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
      
      // If deleted current session, clear messages
      if (currentSession?.session_id === sessionId) {
        const remaining = sessions.filter(s => s.session_id !== sessionId);
        if (remaining.length > 0) {
          setCurrentSession(remaining[0]);
        } else {
          setCurrentSession(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error("Failed to delete session:", err);
      setError("Failed to delete chat");
    }
  };

  const renameSession = async (sessionId, newTitle) => {
    try {
      // Assuming you have update endpoint: PATCH /vectordb/chat_session/module_id/session_id/
      await api.callAPI('post', `/vectordb/edit_session/${sessionId}/`, {
        title: newTitle
      });
      
      setSessions(prev => 
        prev.map(s => s.session_id === sessionId ? { ...s, title: newTitle } : s)
      );
      
      if (currentSession?.session_id === sessionId) {
        setCurrentSession(prev => ({ ...prev, title: newTitle }));
      }
      
      setEditingSessionId(null);
    } catch (err) {
      console.error("Failed to rename session:", err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      text: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const questionText = input.trim();
    setInput("");
    setIsLoading(true);
    setError(null);

    try {
      // Using your chat API
      let endpoint;
      if (currentSession?.session_id) {
        // Existing session: /vectordb/chat/module_id/session_id/
        endpoint = `/vectordb/chat/${moduleId}/${currentSession.session_id}/`;
      } else {
        // New session: /vectordb/chat/module_id/
        endpoint = `/vectordb/chat/${moduleId}/`;
      }
      
      const data = await api.callAPI('post', endpoint, { question: questionText });
      
      // If new session was created, add it to sessions list
      if (!currentSession && data.session_id) {
        const newSession = {
          id: Date.now().toString(),
          session_id: data.session_id,
          title: questionText.substring(0, 50) + (questionText.length > 50 ? '...' : ''),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        setSessions(prev => [newSession, ...prev]);
        setCurrentSession(newSession);
      }
      
      // Remove temp message and add real ones
      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== userMessage.id);
        return [
          ...filtered,
          {
            id: `q-${Date.now()}`,
            role: "user",
            text: data.question,
            timestamp: new Date(),
          },
          {
            id: data.answer_id || `a-${Date.now()}`,
            role: "assistant",
            text: data.answer,
            timestamp: new Date(),
            processingTime: data.processing_time,
            answerId: data.answer_id,
          }
        ];
      });

      // Refresh sessions to get updated timestamp
      loadSessions();

    } catch (err) {
      setError(err.message || "Failed to get response");
      console.error("Chat error:", err);
      
      // Remove temp message
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleRating = async (answerId, score) => {
    try {
      await api.callAPI('post', `/vectordb/rating/${answerId}/`, { score });
      // Optional: Show success feedback
    } catch (err) {
      console.error("Rating error:", err);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div 
        className={`${
          sidebarOpen ? 'w-80' : 'w-0'
        } transition-all duration-300 bg-white border-r border-gray-200 flex flex-col overflow-hidden`}
      >
        {/* Sidebar Header */}
        <div className="p-4 border-b border-gray-200">
          <button
            onClick={createNewSession}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 transition shadow-sm"
          >
            <Plus className="h-4 w-4" />
            <span className="font-medium">New Chat</span>
          </button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto p-3">
          {isLoadingSessions ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <MessageSquare className="h-12 w-12 mx-auto mb-2 text-gray-300" />
              <p className="text-sm">No chats yet</p>
            </div>
          ) : (
            sessions.map(session => (
              <div
                key={session.id}
                onClick={() => setCurrentSession(session)}
                className={`group relative mb-2 p-3 rounded-lg cursor-pointer transition ${
                  currentSession?.session_id === session.session_id
                    ? 'bg-blue-50 border-2 border-blue-200'
                    : 'hover:bg-gray-50 border-2 border-transparent'
                }`}
              >
                {editingSessionId === session.session_id ? (
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onBlur={() => {
                      if (editTitle.trim()) {
                        renameSession(session.session_id, editTitle.trim());
                      } else {
                        setEditingSessionId(null);
                      }
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        renameSession(session.session_id, editTitle.trim());
                      } else if (e.key === 'Escape') {
                        setEditingSessionId(null);
                      }
                    }}
                    className="w-full px-2 py-1 text-sm border border-blue-500 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    autoFocus
                  />
                ) : (
                  <>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex items-start gap-2 flex-1 min-w-0">
                        <MessageSquare className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                        <h3 className="text-sm font-medium text-gray-900 line-clamp-2 leading-snug">
                          {session.title}
                        </h3>
                      </div>
                      
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingSessionId(session.session_id);
                            setEditTitle(session.title);
                          }}
                          className="p-1.5 hover:bg-gray-200 rounded transition"
                          title="Rename"
                        >
                          <Edit2 className="h-3.5 w-3.5 text-gray-600" />
                        </button>
                        <button
                          onClick={(e) => deleteSession(session.session_id, e)}
                          className="p-1.5 hover:bg-red-50 rounded transition"
                          title="Delete"
                        >
                          <Trash2 className="h-3.5 w-3.5 text-red-600" />
                        </button>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <Clock className="h-3 w-3" />
                      <span>{formatDate(session.updated_at || session.created_at)}</span>
                    </div>
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="border-b bg-white px-6 py-4 shadow-sm flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-gray-100 rounded-lg transition"
            >
              {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 flex-shrink-0">
              <Bot className="h-6 w-6 text-white" />
            </div>
            
            <div className="min-w-0 flex-1">
              <h1 className="text-lg font-semibold text-gray-900 truncate">
                {currentSession?.title || "New Chat"}
              </h1>
              <p className="text-sm text-gray-500">
                Ask anything about your documents
              </p>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div
          ref={scrollAreaRef}
          className="flex-1 overflow-y-auto px-4 py-6"
        >
          <div className="mx-auto max-w-4xl space-y-6">
            {messages.length === 0 && !isLoading && (
              <div className="text-center py-12">
                <div className="inline-flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-blue-100 to-indigo-100 mb-4">
                  <MessageSquare className="h-10 w-10 text-blue-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Start a conversation
                </h3>
                <p className="text-gray-600 mb-8 max-w-md mx-auto">
                  Ask questions about your documents and get AI-powered answers with context
                </p>
                <div className="flex flex-wrap gap-2 justify-center max-w-2xl mx-auto">
                  <button
                    onClick={() => setInput("What is the main process described?")}
                    className="px-4 py-2.5 text-sm bg-white border border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition shadow-sm"
                  >
                    📋 What is the main process?
                  </button>
                  <button
                    onClick={() => setInput("How do I configure the system?")}
                    className="px-4 py-2.5 text-sm bg-white border border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition shadow-sm"
                  >
                    ⚙️ How to configure?
                  </button>
                  <button
                    onClick={() => setInput("What are the requirements?")}
                    className="px-4 py-2.5 text-sm bg-white border border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition shadow-sm"
                  >
                    📝 What are the requirements?
                  </button>
                </div>
              </div>
            )}

            {messages.map((message) => {
              const isUser = message.role === "user";
              return (
                <div
                  key={message.id}
                  className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`flex max-w-[85%] gap-3 ${
                      isUser ? "flex-row-reverse" : ""
                    }`}
                  >
                    {/* Avatar */}
                    <div
                      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                        isUser 
                          ? "bg-gradient-to-br from-blue-600 to-indigo-600" 
                          : "bg-gradient-to-br from-gray-100 to-gray-200"
                      }`}
                    >
                      {isUser ? (
                        <User className="h-4 w-4 text-white" />
                      ) : (
                        <Bot className="h-4 w-4 text-gray-700" />
                      )}
                    </div>

                    {/* Message Content */}
                    <div className="space-y-2">
                      <div
                        className={`rounded-xl px-4 py-3 ${
                          isUser
                            ? "bg-gradient-to-br from-blue-600 to-indigo-600 text-white"
                            : "bg-white text-gray-900 shadow-sm border border-gray-200"
                        }`}
                      >
                        <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                          {message.text}
                        </p>
                      </div>

                      {/* Processing Time & Rating */}
                      {!isUser && message.processingTime && (
                        <div className="flex items-center gap-3 px-2">
                          <div className="flex items-center gap-1 text-xs text-gray-500">
                            <Clock className="h-3 w-3" />
                            <span>{message.processingTime.toFixed(2)}s</span>
                          </div>
                          {message.answerId && (
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleRating(message.answerId, 5)}
                                className="text-gray-400 hover:text-green-600 transition"
                                title="Good answer"
                              >
                                <ThumbsUp className="h-4 w-4" />
                              </button>
                              <button
                                onClick={() => handleRating(message.answerId, 1)}
                                className="text-gray-400 hover:text-red-600 transition"
                                title="Bad answer"
                              >
                                <ThumbsDown className="h-4 w-4" />
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-gray-100 to-gray-200">
                    <Bot className="h-4 w-4 text-gray-700" />
                  </div>
                  <div className="flex items-center gap-2 rounded-xl bg-white px-4 py-3 shadow-sm border border-gray-200">
                    <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                    <span className="text-sm text-gray-600">Thinking...</span>
                  </div>
                </div>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="mx-auto max-w-md">
                <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 shadow-sm">
                  <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-red-700 font-medium mb-1">Error</p>
                    <p className="text-sm text-red-600">{error}</p>
                    <button
                      onClick={() => setError(null)}
                      className="text-xs text-red-500 hover:text-red-700 mt-2 font-medium"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Input Area */}
        <div className="border-t bg-white px-4 py-4 shadow-lg flex-shrink-0">
          <div className="mx-auto max-w-4xl">
            <form onSubmit={handleSubmit} className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question about your documents..."
                disabled={isLoading}
                className="flex-1 rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50 transition"
                autoFocus
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-3 text-sm font-medium text-white hover:from-blue-700 hover:to-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 transition shadow-sm"
              >
                <Send className="h-4 w-4" />
                <span className="hidden sm:inline">Send</span>
              </button>
            </form>
            {input.length > 0 && (
              <div className="mt-2 text-right text-xs text-gray-500">
                {input.length} / 2000 characters
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
