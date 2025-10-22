"use client";

import { useState, useEffect, useRef, use } from "react";
import { Send, Bot, User, Loader2, AlertCircle, ThumbsUp, ThumbsDown } from "lucide-react";
import api from '@/lib/api';

export default function ChatPage({ params }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const scrollAreaRef = useRef(null);
  const inputRef = useRef(null);
  const unwrappedParams = use(params);
  const moduleId = unwrappedParams.moduleId;

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  // Welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          id: "welcome",
          role: "assistant",
          text: "Hello! I'm your RAG assistant. Ask me anything about your documents.",
          timestamp: new Date(),
        },
      ]);
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: Date.now().toString(),
      role: "user",
      text: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setError(null);

    try {
      const data = await api.callAPI('post', `/vectordb/chat/${moduleId}/`, { question: input });
      console.log("Response Data: ", data);
      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        text: data.answer,
        timestamp: new Date(),
        processingTime: data.processing_time,
        answerId: data.answer_id, // if you add it in response
      };

      setMessages((prev) => [...prev, assistantMessage]);

      console.log("messages: ", messages);
      inputRef.current?.focus();
    } catch (err) {
      setError(err.message);
      console.error("Chat error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRating = async (answerId, score) => {
    try {
      const data = await api.callAPI('post', `/vectordb/rating/${answerId}/`, { "rating": score });
    } catch (err) {
      console.error("Rating error:", err);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      {/* Header */}
      <div className="border-b bg-white px-6 py-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600">
            <Bot className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">
              RAG Chat Assistant
            </h1>
            <p className="text-sm text-gray-500">
              Powered by your vector database
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
          {messages.map((message) => {
            console.log("Rendering message: ", message);
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
                        ? "bg-blue-600"
                        : "bg-gray-200"
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
                      className={`rounded-lg px-4 py-3 ${
                        isUser
                          ? "bg-blue-600 text-white"
                          : "bg-white text-gray-900 shadow-sm"
                      }`}
                    >
                      <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                        {message.text}
                      </p>
                    </div>

                    {/* Processing Time & Rating */}
                    {!isUser && message.processingTime && (
                      <div className="flex items-center gap-3 px-2">
                        <span className="text-xs text-gray-500">
                          {message.processingTime.toFixed(2)}s
                        </span>
                        {message.answerId && (
                          <div className="flex gap-2">
                            <button
                              onClick={() =>
                                handleRating(message.answerId, 5)
                              }
                              className="text-gray-400 hover:text-green-600"
                            >
                              <ThumbsUp className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() =>
                                handleRating(message.answerId, 1)
                              }
                              className="text-gray-400 hover:text-red-600"
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
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200">
                  <Bot className="h-4 w-4 text-gray-700" />
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-white px-4 py-3 shadow-sm">
                  <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
                  <span className="text-sm text-gray-500">Thinking...</span>
                </div>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mx-auto max-w-md">
              <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3">
                <AlertCircle className="h-4 w-4 text-red-600" />
                <p className="text-sm text-red-600">{error}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t bg-white px-4 py-4 shadow-lg">
        <div className="mx-auto max-w-4xl">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about your documents..."
              disabled={isLoading}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              autoFocus
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>
          {input.length > 0 && (
            <div className="mt-2 text-right text-xs text-gray-500">
              {input.length} characters
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
