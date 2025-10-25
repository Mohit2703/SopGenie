"use client";

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  UserPlus, X, Search, Trash2, Shield, Eye, Edit3, 
  Loader2, Check, AlertCircle 
} from 'lucide-react';
import api from '@/lib/api';

export default function UserManagement({ projectId }) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedRole, setSelectedRole] = useState('viewer');
  const [error, setError] = useState('');
  const queryClient = useQueryClient();

  // Fetch project members
  const { data: membersData, isLoading } = useQuery({
    queryKey: ['project-members', projectId],
    queryFn: async () => {
      const userData = await api.callAPI('get', `/projects/${projectId}/members/`);
      console.log('userData: ', userData);
      return userData;
    },
  });

  // Search users
  const { data: searchResults } = useQuery({
    queryKey: ['search-users', searchQuery],
    queryFn: async () => {
      if (searchQuery.length < 2) return { users: [] };
      return await api.callAPI('get', `/search_users/?q=${searchQuery}`);
    },
    enabled: searchQuery.length >= 2,
  });

  // Add member mutation
  const addMemberMutation = useMutation({
    mutationFn: async ({ userIdentifier, role }) => {
      return await api.callAPI('post', `/projects/${projectId}/members/`, {
        user_id: userIdentifier,
        role: role,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['project-members', projectId]);
      setShowAddModal(false);
      setSearchQuery('');
      setSelectedUser(null);
      setError('');
    },
    onError: (error) => {
      setError(error.response?.data?.error || 'Failed to add member');
    },
  });

  // Remove member mutation
  const removeMemberMutation = useMutation({
    mutationFn: async (memberId) => {
      return await api.callAPI('delete', `/projects/${projectId}/members/${memberId}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['project-members', projectId]);
    },
  });

  // Update member role mutation
  const updateRoleMutation = useMutation({
    mutationFn: async ({ memberId, role }) => {
      return await api.callAPI('patch', `/projects/${projectId}/members/${memberId}/`, {
        role: role,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['project-members', projectId]);
    },
  });

  const handleAddMember = () => {
    if (!selectedUser) {
      setError('Please select a user');
      return;
    }
    addMemberMutation.mutate({
      userIdentifier: selectedUser.id,
      role: selectedRole,
    });
  };

  const getRoleIcon = (role) => {
    switch (role) {
      case 'owner':
        return <Shield className="h-4 w-4 text-purple-600" />;
      case 'admin':
        return <Edit3 className="h-4 w-4 text-blue-600" />;
      case 'editor':
        return <Edit3 className="h-4 w-4 text-green-600" />;
      default:
        return <Eye className="h-4 w-4 text-gray-600" />;
    }
  };

  const getRoleBadgeColor = (role) => {
    switch (role) {
      case 'owner':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'admin':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'editor':
        return 'bg-green-100 text-green-700 border-green-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Team Members</h2>
          <p className="text-sm text-gray-600 mt-1">
            Manage who has access to this project
          </p>
        </div>
        {(membersData?.user_role === 'owner' || membersData?.user_role === 'admin') && (
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            <UserPlus className="h-4 w-4" />
            Add Member
          </button>
        )}
      </div>

      {/* Members List */}
      <div className="space-y-3">
        {membersData?.members?.map((member) => (
          <div
            key={member.id}
            className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
          >
            <div className="flex items-center gap-4">
              <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-semibold">
                {member.user.name
                  ? member.user.name[0].toUpperCase()
                  : member.user.username[0].toUpperCase()}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-medium text-gray-900">
                    {member.user.name
                      ? `${member.user.name}`
                      : member.user.username}
                  </p>
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${getRoleBadgeColor(
                      member.role
                    )}`}
                  >
                    {getRoleIcon(member.role)}
                    {member.role}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{member.user.email}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {(membersData.user_role === 'owner' || membersData.user_role === 'admin') && 
              (
                <>
                  <select
                    value={member.role}
                    onChange={(e) =>
                      updateRoleMutation.mutate({
                        memberId: member.id,
                        role: e.target.value,
                      })
                    }
                    className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="viewer">Viewer</option>
                    <option value="editor">Editor</option>
                    <option value="admin">Admin</option>
                  </select>
                  <button
                    onClick={() => {
                      if (confirm('Remove this member from the project?')) {
                        removeMemberMutation.mutate(member.id);
                      }
                    }}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                    title="Remove member"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Add Member Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-6 border-b">
              <h3 className="text-xl font-bold text-gray-900">Add Team Member</h3>
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setSearchQuery('');
                  setSelectedUser(null);
                  setError('');
                }}
                className="p-2 hover:bg-gray-100 rounded-lg transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {error && (
                <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              {/* Search Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Search User
                </label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by name, username, or email..."
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Search Results */}
              {searchQuery.length >= 2 && (
                <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-lg">
                  {searchResults?.users?.length > 0 ? (
                    searchResults.users.map((user) => (
                      <button
                        key={user.id}
                        onClick={() => {
                          setSelectedUser(user);
                          setSearchQuery('');
                        }}
                        className="w-full flex items-center gap-3 p-3 hover:bg-blue-50 transition text-left"
                      >
                        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-sm font-semibold">
                          {user.display_name[0].toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-gray-900 truncate">
                            {user.display_name}
                          </p>
                          <p className="text-sm text-gray-600 truncate">{user.email}</p>
                        </div>
                      </button>
                    ))
                  ) : (
                    <p className="p-3 text-sm text-gray-600 text-center">
                      No users found
                    </p>
                  )}
                </div>
              )}

              {/* Selected User */}
              {selectedUser && (
                <div className="flex items-center gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-semibold">
                    {selectedUser.display_name[0].toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900">{selectedUser.display_name}</p>
                    <p className="text-sm text-gray-600">{selectedUser.email}</p>
                  </div>
                  <button
                    onClick={() => setSelectedUser(null)}
                    className="p-1 hover:bg-blue-100 rounded"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}

              {/* Role Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Role
                </label>
                <select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="viewer">Viewer - Can view only</option>
                  <option value="editor">Editor - Can view and edit</option>
                  <option value="admin">Admin - Full access except ownership</option>
                </select>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => {
                    setShowAddModal(false);
                    setSearchQuery('');
                    setSelectedUser(null);
                    setError('');
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddMember}
                  disabled={!selectedUser || addMemberMutation.isPending}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
                >
                  {addMemberMutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    <>
                      <Check className="h-4 w-4" />
                      Add Member
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
