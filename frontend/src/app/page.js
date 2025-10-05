'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { BookOpen, Database, MessageSquare, Upload } from 'lucide-react';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('Token');
    if (!token) {
      router.push('/login');
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            SOP RAG System
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Transform your Standard Operating Procedures with AI-powered search and intelligent document management
          </p>
          <div className="space-x-4">
            <button
              onClick={() => router.push('/dashboard')}
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg text-lg font-semibold"
            >
              Get Started
            </button>
            <button
              onClick={() => router.push('/login')}
              className="bg-white hover:bg-gray-50 text-blue-600 px-8 py-3 rounded-lg text-lg font-semibold border border-blue-600"
            >
              Login
            </button>
          </div>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 max-w-6xl mx-auto">
          <div className="bg-white p-6 rounded-lg shadow-md text-center">
            <Upload className="h-12 w-12 text-blue-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Document Upload</h3>
            <p className="text-gray-600">
              Easily upload and manage your SOP documents
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-md text-center">
            <Database className="h-12 w-12 text-green-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Vector Database</h3>
            <p className="text-gray-600">
              Automatic vectorization and intelligent indexing
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-md text-center">
            <MessageSquare className="h-12 w-12 text-purple-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">AI Chat</h3>
            <p className="text-gray-600">
              Ask questions and get instant answers from your SOPs
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-md text-center">
            <BookOpen className="h-12 w-12 text-orange-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibull mb-2">Smart Search</h3>
            <p className="text-gray-600">
              Find relevant procedures with semantic search
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
