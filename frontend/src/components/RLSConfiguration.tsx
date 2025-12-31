import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Edit2, Save, X, Shield, Users, Lock } from 'lucide-react';
import { api } from '../api/client';

interface RLSFilter {
  id?: number;
  user_id: number;
  connection_id: number;
  table_name: string;
  column_name: string;
  operator: string;
  filter_value: any;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

interface UserRole {
  id?: number;
  user_id: number;
  connection_id: number;
  role: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
}

interface Connection {
  id: number;
  name: string;
  database_type: string;
}

interface TableColumn {
  table_name: string;
  columns: string[];
}

const OPERATORS = ['=', '!=', '>', '<', '>=', '<=', 'IN', 'NOT IN', 'LIKE', 'NOT LIKE', 'IS NULL', 'IS NOT NULL'];
const ROLES = ['ADMIN', 'ANALYST', 'VIEWER', 'EXTERNAL', 'CUSTOM'];

export const RLSConfiguration: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [selectedUser, setSelectedUser] = useState<number | null>(null);
  const [selectedConnection, setSelectedConnection] = useState<number | null>(null);
  const [userRole, setUserRole] = useState<UserRole | null>(null);
  const [rlsFilters, setRlsFilters] = useState<RLSFilter[]>([]);
  const [tables, setTables] = useState<TableColumn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [editingFilter, setEditingFilter] = useState<RLSFilter | null>(null);
  const [showAddFilter, setShowAddFilter] = useState(false);

  // Load users and connections on mount
  useEffect(() => {
    loadUsers();
    loadConnections();
  }, []);

  // Load user configuration when selection changes
  useEffect(() => {
    if (selectedUser && selectedConnection) {
      loadUserRLSConfig();
      loadTables();
    }
  }, [selectedUser, selectedConnection]);

  const loadUsers = async () => {
    try {
      const response = await api.get('/users');
      setUsers(response.data);
    } catch (err: any) {
      setError('Failed to load users: ' + err.message);
    }
  };

  const loadConnections = async () => {
    try {
      const response = await api.get('/connections');
      setConnections(response.data);
    } catch (err: any) {
      setError('Failed to load connections: ' + err.message);
    }
  };

  const loadUserRLSConfig = async () => {
    if (!selectedUser || !selectedConnection) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get(`/rls/config/user/${selectedUser}/connection/${selectedConnection}`);
      const config = response.data;
      
      setUserRole(config.role ? {
        user_id: config.user_id,
        connection_id: config.connection_id,
        role: config.role,
      } : null);
      
      setRlsFilters(config.rls_filters || []);
    } catch (err: any) {
      if (err.response?.status !== 404) {
        setError('Failed to load RLS configuration: ' + err.message);
      }
      setUserRole(null);
      setRlsFilters([]);
    } finally {
      setLoading(false);
    }
  };

  const loadTables = async () => {
    if (!selectedConnection) return;
    
    try {
      const response = await api.get(`/connections/${selectedConnection}/schema`);
      setTables(response.data);
    } catch (err: any) {
      console.error('Failed to load tables:', err);
    }
  };

  const saveUserRole = async (role: string) => {
    if (!selectedUser || !selectedConnection) return;
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      await api.post('/rls/roles', {
        user_id: selectedUser,
        connection_id: selectedConnection,
        role,
      });
      
      setSuccess('Role assigned successfully');
      await loadUserRLSConfig();
    } catch (err: any) {
      setError('Failed to assign role: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const saveRLSFilter = async (filter: RLSFilter) => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      if (filter.id) {
        // Update existing
        await api.put(`/rls/filters/${filter.id}`, {
          operator: filter.operator,
          filter_value: filter.filter_value,
          is_active: filter.is_active,
        });
      } else {
        // Create new
        await api.post('/rls/filters', filter);
      }
      
      setSuccess('RLS filter saved successfully');
      setEditingFilter(null);
      setShowAddFilter(false);
      await loadUserRLSConfig();
    } catch (err: any) {
      setError('Failed to save RLS filter: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteRLSFilter = async (filterId: number) => {
    if (!confirm('Are you sure you want to delete this RLS filter?')) return;
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      await api.delete(`/rls/filters/${filterId}`);
      setSuccess('RLS filter deleted successfully');
      await loadUserRLSConfig();
    } catch (err: any) {
      setError('Failed to delete RLS filter: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const renderRoleSelector = () => {
    if (!selectedUser || !selectedConnection) return null;

    return (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center mb-4">
          <Shield className="h-5 w-5 text-blue-600 mr-2" />
          <h3 className="text-lg font-semibold">User Role</h3>
        </div>
        
        <div className="flex items-center gap-4">
          <select
            value={userRole?.role || ''}
            onChange={(e) => saveUserRole(e.target.value)}
            disabled={loading}
            className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Select Role...</option>
            {ROLES.map(role => (
              <option key={role} value={role}>{role}</option>
            ))}
          </select>
          
          {userRole && (
            <span className="px-3 py-2 bg-blue-100 text-blue-800 rounded-lg font-medium">
              Current: {userRole.role}
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderFilterEditor = (filter: RLSFilter, isNew: boolean = false) => {
    const [localFilter, setLocalFilter] = useState<RLSFilter>(filter);

    return (
      <div className="border rounded-lg p-4 bg-gray-50">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Table</label>
            <select
              value={localFilter.table_name}
              onChange={(e) => setLocalFilter({ ...localFilter, table_name: e.target.value, column_name: '' })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select Table...</option>
              {tables.map(t => (
                <option key={t.table_name} value={t.table_name}>{t.table_name}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Column</label>
            <select
              value={localFilter.column_name}
              onChange={(e) => setLocalFilter({ ...localFilter, column_name: e.target.value })}
              disabled={!localFilter.table_name}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select Column...</option>
              {tables
                .find(t => t.table_name === localFilter.table_name)
                ?.columns.map(col => (
                  <option key={col} value={col}>{col}</option>
                ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Operator</label>
            <select
              value={localFilter.operator}
              onChange={(e) => setLocalFilter({ ...localFilter, operator: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select Operator...</option>
              {OPERATORS.map(op => (
                <option key={op} value={op}>{op}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Value</label>
            <input
              type="text"
              value={typeof localFilter.filter_value === 'string' ? localFilter.filter_value : JSON.stringify(localFilter.filter_value)}
              onChange={(e) => {
                try {
                  const parsed = JSON.parse(e.target.value);
                  setLocalFilter({ ...localFilter, filter_value: parsed });
                } catch {
                  setLocalFilter({ ...localFilter, filter_value: e.target.value });
                }
              }}
              placeholder={localFilter.operator === 'IN' ? '["value1", "value2"]' : '"Region 1"'}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              {localFilter.operator === 'IN' ? 'Use JSON array format' : 'Use JSON string format'}
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <button
            onClick={() => {
              setEditingFilter(null);
              setShowAddFilter(false);
            }}
            className="px-4 py-2 text-gray-700 bg-white border rounded-lg hover:bg-gray-50"
          >
            <X className="h-4 w-4 inline mr-1" />
            Cancel
          </button>
          <button
            onClick={() => saveRLSFilter(localFilter)}
            disabled={!localFilter.table_name || !localFilter.column_name || !localFilter.operator || !localFilter.filter_value}
            className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <Save className="h-4 w-4 inline mr-1" />
            Save Filter
          </button>
        </div>
      </div>
    );
  };

  const renderFilters = () => {
    if (!selectedUser || !selectedConnection) return null;

    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <Lock className="h-5 w-5 text-blue-600 mr-2" />
            <h3 className="text-lg font-semibold">RLS Filters</h3>
          </div>
          <button
            onClick={() => {
              setShowAddFilter(true);
              setEditingFilter({
                user_id: selectedUser,
                connection_id: selectedConnection,
                table_name: '',
                column_name: '',
                operator: '=',
                filter_value: '',
              });
            }}
            className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700"
          >
            <Plus className="h-4 w-4 inline mr-1" />
            Add Filter
          </button>
        </div>

        {showAddFilter && editingFilter && (
          <div className="mb-4">
            {renderFilterEditor(editingFilter, true)}
          </div>
        )}

        {rlsFilters.length === 0 && !showAddFilter ? (
          <div className="text-center py-8 text-gray-500">
            <Lock className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No RLS filters configured</p>
            <p className="text-sm">Add filters to restrict data access</p>
          </div>
        ) : (
          <div className="space-y-3">
            {rlsFilters.map((filter) => (
              <div key={filter.id} className="border rounded-lg p-4 hover:bg-gray-50">
                {editingFilter?.id === filter.id ? (
                  renderFilterEditor(filter)
                ) : (
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">
                        {filter.table_name}.{filter.column_name}
                      </div>
                      <div className="text-sm text-gray-600">
                        {filter.operator} {typeof filter.filter_value === 'string' ? filter.filter_value : JSON.stringify(filter.filter_value)}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        Updated: {new Date(filter.updated_at || '').toLocaleDateString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 text-xs rounded ${filter.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                        {filter.is_active ? 'Active' : 'Inactive'}
                      </span>
                      <button
                        onClick={() => setEditingFilter(filter)}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => deleteRLSFilter(filter.id!)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">RLS Configuration</h1>
        <p className="text-gray-600">Configure row-level security filters and roles for users</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700">
          {success}
        </div>
      )}

      {/* User and Connection Selection */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center mb-4">
          <Users className="h-5 w-5 text-blue-600 mr-2" />
          <h3 className="text-lg font-semibold">Select User & Connection</h3>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">User</label>
            <select
              value={selectedUser || ''}
              onChange={(e) => setSelectedUser(Number(e.target.value))}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Select User...</option>
              {users.map(user => (
                <option key={user.id} value={user.id}>
                  {user.full_name || user.username} ({user.email})
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Connection</label>
            <select
              value={selectedConnection || ''}
              onChange={(e) => setSelectedConnection(Number(e.target.value))}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Select Connection...</option>
              {connections.map(conn => (
                <option key={conn.id} value={conn.id}>
                  {conn.name} ({conn.database_type})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {selectedUser && selectedConnection && (
        <>
          {renderRoleSelector()}
          {renderFilters()}
        </>
      )}

      {loading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-700">Loading...</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default RLSConfiguration;
