"use client";

import { useUser } from '@/lib/contexts/UserContext';
import { LogOut, User, Settings, ChevronDown } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function UserHeader() {
  const { user, logout } = useUser();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const router = useRouter();

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  if (!user) return null;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setDropdownOpen(!dropdownOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition"
      >
        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center">
          <User className="h-5 w-5 text-white" />
        </div>
        <div className="text-left hidden sm:block">
          <p className="text-sm font-medium text-gray-900">
            {user.first_name && user.last_name 
              ? `${user.first_name} ${user.last_name}` 
              : user.username}
          </p>
          <p className="text-xs text-gray-500">{user.email}</p>
        </div>
        <ChevronDown className={`h-4 w-4 text-gray-500 transition ${dropdownOpen ? 'rotate-180' : ''}`} />
      </button>

      {dropdownOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
          <div className="px-4 py-3 border-b border-gray-200">
            <p className="text-sm font-medium text-gray-900">
              {user.first_name && user.last_name 
                ? `${user.first_name} ${user.last_name}` 
                : user.username}
            </p>
            <p className="text-xs text-gray-500">{user.email}</p>
            {user.role && (
              <p className="text-xs text-blue-600 mt-1 font-medium">
                {user.role}
              </p>
            )}
          </div>

          <button
            onClick={() => {
              router.push('/settings');
              setDropdownOpen(false);
            }}
            className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            <Settings className="h-4 w-4" />
            Settings
          </button>

          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </div>
      )}
    </div>
  );
}
