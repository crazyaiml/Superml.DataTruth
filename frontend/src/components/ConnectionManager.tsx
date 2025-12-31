import React, { useState, useEffect } from 'react';
import axios from 'axios';
// import { Database, Plus, Server, CheckCircle, XCircle, Search, X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { API_URL } from '../config';

interface Connection {
  id: string;
  name: string;
  type: string;
  host?: string;
  port?: number;
  database: string;
  is_active: boolean;
  created_at?: string;
}

interface ConnectionFormData {
  id: string;
  name: string;
  type: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  schema_name: string;
}

const ConnectionManager: React.FC = () => {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [discovering, setDiscovering] = useState<string | null>(null);
  const [editingConnection, setEditingConnection] = useState<string | null>(null);

  const [formData, setFormData] = useState<ConnectionFormData>({
    id: '',
    name: '',
    type: 'postgresql',
    host: 'localhost',
    port: 5432,
    database: '',
    username: '',
    password: '',
    schema_name: 'public'
  });

  const { token } = useAuth();

  useEffect(() => {
    if (token) {
      loadConnections();
    }
  }, [token]);

  const loadConnections = async () => {
    if (!token) return;
    
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/v1/connections`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setConnections(response.data.connections || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load connections');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    try {
      setLoading(true);
      
      if (editingConnection) {
        // Update existing connection
        await axios.put(
          `${API_URL}/api/v1/connections/${editingConnection}`,
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setSuccess('Connection updated successfully!');
      } else {
        // Create new connection
        await axios.post(
          `${API_URL}/api/v1/connections`,
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setSuccess('Connection created successfully!');
      }
      
      setShowForm(false);
      setEditingConnection(null);
      loadConnections();
      // Reset form
      setFormData({
        id: '',
        name: '',
        type: 'postgresql',
        host: 'localhost',
        port: 5432,
        database: '',
        username: '',
        password: '',
        schema_name: 'public'
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to ${editingConnection ? 'update' : 'create'} connection`);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (connection: Connection) => {
    setEditingConnection(connection.id);
    setFormData({
      id: connection.id,
      name: connection.name,
      type: connection.type,
      host: connection.host || 'localhost',
      port: connection.port || 5432,
      database: connection.database,
      username: '',
      password: '',
      schema_name: 'public'
    });
    setShowForm(true);
    setError(null);
    setSuccess(null);
  };

  const handleDiscover = async (connectionId: string) => {
    setError(null);
    setSuccess(null);
    setDiscovering(connectionId);

    try {
      const response = await axios.post(
        `${API_URL}/api/v1/connections/${connectionId}/discover`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSuccess(
        `Schema discovered! Found ${response.data.table_count} tables and ${response.data.relationship_count} relationships.`
      );
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Schema discovery failed');
    } finally {
      setDiscovering(null);
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Connection Manager</h2>
            <p className="mt-1 text-sm text-gray-500">
              Manage database connections and discover schemas
            </p>
          </div>
          <button
            onClick={() => {
              if (showForm) {
                setShowForm(false);
                setEditingConnection(null);
                setFormData({
                  id: '',
                  name: '',
                  type: 'postgresql',
                  host: 'localhost',
                  port: 5432,
                  database: '',
                  username: '',
                  password: '',
                  schema_name: 'public'
                });
              } else {
                setShowForm(true);
              }
            }}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
          >
            {showForm ? 'Cancel' : '+ New Connection'}
          </button>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="mx-6 mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-800">{error}</p>
        </div>
      )}
      {success && (
        <div className="mx-6 mt-4 p-4 bg-green-50 border border-green-200 rounded-md">
          <p className="text-green-800">{success}</p>
        </div>
      )}

      {/* Connection Form */}
      {showForm && (
        <div className="mx-6 mt-4 bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">{editingConnection ? 'Edit Connection' : 'Create New Connection'}</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Connection ID *
                </label>
                <input
                  type="text"
                  value={formData.id}
                  onChange={(e) => setFormData({ ...formData, id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  required
                  placeholder="main-db"
                  disabled={!!editingConnection}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Connection Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  required
                  placeholder="Main Database"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Database Type *
                </label>
                <select
                  value={formData.type}
                  onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="postgresql">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                  <option value="snowflake">Snowflake</option>
                  <option value="redshift">Redshift</option>
                  <option value="bigquery">BigQuery</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Host *</label>
                <input
                  type="text"
                  value={formData.host}
                  onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Port *</label>
                <input
                  type="number"
                  value={formData.port}
                  onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Database Name *
                </label>
                <input
                  type="text"
                  value={formData.database}
                  onChange={(e) => setFormData({ ...formData, database: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Schema</label>
                <input
                  type="text"
                  value={formData.schema_name}
                  onChange={(e) => setFormData({ ...formData, schema_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Username *
                </label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password *
                </label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  required
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:bg-gray-400"
              >
                {loading ? (editingConnection ? 'Updating...' : 'Creating...') : (editingConnection ? 'Update Connection' : 'Create Connection')}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Connections List */}
      <div className="flex-1 overflow-auto p-6">
        {loading && !showForm ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            <p className="mt-2 text-gray-600">Loading connections...</p>
          </div>
        ) : connections.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-gray-300">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
              />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No connections</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by creating a new database connection.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {connections.map((conn) => (
              <div
                key={conn.id}
                className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{conn.name}</h3>
                    <p className="text-sm text-gray-500 font-mono">{conn.id}</p>
                  </div>
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${
                      conn.is_active
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {conn.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>

                <div className="space-y-2 mb-4">
                  <div className="flex items-center text-sm">
                    <span className="text-gray-500 w-20">Type:</span>
                    <span className="font-medium text-gray-900">{conn.type}</span>
                  </div>
                  <div className="flex items-center text-sm">
                    <span className="text-gray-500 w-20">Host:</span>
                    <span className="font-medium text-gray-900">{conn.host || 'N/A'}</span>
                  </div>
                  <div className="flex items-center text-sm">
                    <span className="text-gray-500 w-20">Database:</span>
                    <span className="font-medium text-gray-900">{conn.database}</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <button
                    onClick={() => handleEdit(conn)}
                    className="w-full px-3 py-2 bg-gray-50 text-gray-700 rounded-md hover:bg-gray-100 transition-colors text-sm font-medium border border-gray-300"
                  >
                    ✏️ Edit Connection
                  </button>
                  <button
                    onClick={() => handleDiscover(conn.id)}
                    disabled={discovering === conn.id}
                    className="w-full px-3 py-2 bg-indigo-50 text-indigo-700 rounded-md hover:bg-indigo-100 transition-colors disabled:bg-gray-100 disabled:text-gray-500 text-sm font-medium"
                  >
                    {discovering === conn.id ? (
                      <>
                        <span className="inline-block animate-spin mr-2">⚙️</span>
                        Discovering...
                      </>
                    ) : (
                      '🔍 Discover Schema'
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ConnectionManager;
