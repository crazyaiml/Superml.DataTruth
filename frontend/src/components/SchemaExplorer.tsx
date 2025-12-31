import React, { useState, useEffect } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { API_URL } from '../config';
// import {
//   Database,
//   Table2,
//   Key,
//   Link,
//   Search,
//   ChevronRight,
//   RefreshCw,
//   Sparkles,
//   Loader2,
// } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface TableMetadata {
  name: string;
  table_type: string;
  row_count: number;
  columns: ColumnMetadata[];
  primary_keys: string[];
}

interface ColumnMetadata {
  name: string;
  data_type: string;
  is_measure: boolean;
  is_dimension: boolean;
  default_aggregation?: string;
  display_name?: string;
  description?: string;
}

interface Relationship {
  from_table: string;
  from_column: string;
  to_table: string;
  to_column: string;
  cardinality: string;
}

interface SchemaData {
  connection_id: string;
  schema_name: string;
  table_count: number;
  relationship_count: number;
  tables: { [key: string]: TableMetadata };
  relationships: Relationship[];
}

const SchemaExplorer: React.FC<{ 
  connectionId: string;
  onConnectionChange?: (connectionId: string) => void;
}> = ({ connectionId, onConnectionChange }) => {
  const [schema, setSchema] = useState<SchemaData | null>(null);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatingAI, setGeneratingAI] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [connections, setConnections] = useState<any[]>([]);

  const { token } = useAuth();

  // Load available connections
  useEffect(() => {
    if (token) {
      loadConnections();
    }
  }, [token]);

  const loadConnections = async () => {
    if (!token) return;
    try {
      const response = await axios.get(`${API_URL}/api/v1/connections`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const loadedConnections = response.data.connections || response.data || [];
      setConnections(loadedConnections);
      // If no connection is selected but we have connections, select the first one
      if (!connectionId && loadedConnections.length > 0 && onConnectionChange) {
        onConnectionChange(loadedConnections[0].id);
      }
    } catch (err) {
      console.error('Failed to load connections:', err);
    }
  };

  useEffect(() => {
    if (connectionId && token) {
      loadSchema();
    }
  }, [connectionId, token]);

  const loadSchema = async () => {
    try {
      setLoading(true);
      setError(null);
      // Trigger discover to get all tables
      await discoverSchema();
    } catch (err: any) {
      if (err.response?.status === 404) {
        // Schema not discovered yet, trigger discovery
        await discoverSchema();
      } else {
        setError(err.response?.data?.detail || 'Failed to load schema');
      }
    } finally {
      setLoading(false);
    }
  };

  const discoverSchema = async () => {
    try {
      setLoading(true);
      const response = await axios.post(
        `${API_URL}/api/v1/connections/${connectionId}/discover`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSchema(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Schema discovery failed');
    } finally {
      setLoading(false);
    }
  };

  const generateAIDescriptions = async (tableName: string) => {
    try {
      setGeneratingAI(true);
      setError(null);
      await axios.post(
        `${API_URL}/api/v1/fieldmap/describe`,
        {
          connection_id: connectionId,
          table_name: tableName
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`AI descriptions generated for ${tableName}!`);
      // Reload table to see updated descriptions
      loadTableDetails(tableName);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'AI description generation failed');
    } finally {
      setGeneratingAI(false);
    }
  };

  const loadTableDetails = async (tableName: string) => {
    try {
      const response = await axios.get(
        `${API_URL}/api/v1/connections/${connectionId}/schema/${tableName}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      // Update the table in schema
      if (schema) {
        setSchema({
          ...schema,
          tables: {
            ...schema.tables,
            [tableName]: response.data
          }
        });
      }
    } catch (err: any) {
      console.error('Failed to load table details:', err);
    }
  };

  const filteredTables = schema
    ? Object.entries(schema.tables).filter(([name]) =>
        name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : [];

  const selectedTableData = selectedTable ? schema?.tables[selectedTable] : null;

  const getRelationshipsForTable = (tableName: string): Relationship[] => {
    if (!schema) return [];
    return schema.relationships.filter(
      (rel) => rel.from_table === tableName || rel.to_table === tableName
    );
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          <p className="mt-4 text-gray-600">Discovering schema...</p>
          <p className="text-sm text-gray-500">This may take a few moments</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="text-red-600 text-4xl mb-4">⚠️</div>
          <p className="text-red-800">{error}</p>
          <button
            onClick={loadSchema}
            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="h-full flex flex-col bg-gray-50">
        {/* Connection Selector Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Schema Explorer</h2>
              <p className="text-sm text-gray-500 mt-1">
                View and manage your database schema, relationships, and semantic layer
              </p>
            </div>
            {connections.length > 0 && (
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700">Connection:</label>
                <select
                  value={connectionId}
                  onChange={(e) => onConnectionChange?.(e.target.value)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="">Select a connection...</option>
                  {connections.map((conn) => (
                    <option key={conn.id} value={conn.id}>
                      {conn.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            {!connectionId ? (
              <>
                <p className="text-gray-600">Select a connection to explore its schema</p>
                {connections.length === 0 && (
                  <p className="text-sm text-gray-500 mt-2">
                    No connections available. Create one in the Connections tab first.
                  </p>
                )}
              </>
            ) : (
              <>
                <p className="text-gray-600">No schema loaded</p>
                <button
                  onClick={loadSchema}
                  className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                >
                  Discover Schema
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Connection Selector Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Schema Explorer</h2>
            <p className="text-sm text-gray-500 mt-1">
              View and manage your database schema, relationships, and semantic layer
            </p>
          </div>
          {connections.length > 0 && (
            <div className="flex items-center gap-3">
              <label className="text-sm font-medium text-gray-700">Connection:</label>
              <select
                value={connectionId}
                onChange={(e) => onConnectionChange?.(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                {connections.map((conn) => (
                  <option key={conn.id} value={conn.id}>
                    {conn.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Tables List */}
        <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
          <div className="p-4 border-b border-gray-200">
            <h3 className="font-semibold text-gray-900 mb-2">
              Tables {schema && `(${schema.table_count})`}
            </h3>
            <input
              type="text"
              placeholder="Search tables..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>

        <div className="flex-1 overflow-auto">
          {filteredTables.map(([name, table]) => (
            <div
              key={name}
              onClick={() => setSelectedTable(name)}
              className={`p-4 border-b border-gray-100 cursor-pointer hover:bg-gray-50 ${
                selectedTable === name ? 'bg-indigo-50 border-l-4 border-l-indigo-600' : ''
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-gray-900">{name}</span>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium ${
                    table.table_type === 'fact'
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-green-100 text-green-800'
                  }`}
                >
                  {table.table_type}
                </span>
              </div>
              <div className="text-xs text-gray-500">
                {table.columns.length} columns • {table.row_count.toLocaleString()} rows
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Table Details */}
      <div className="flex-1 overflow-auto">
        {selectedTableData ? (
          <div className="p-6">
            {/* Table Header */}
            <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">{selectedTable}</h2>
                  <p className="text-gray-500 mt-1">
                    {selectedTableData.row_count.toLocaleString()} rows •{' '}
                    {selectedTableData.columns.length} columns
                  </p>
                </div>
                <button
                  onClick={() => generateAIDescriptions(selectedTable!)}
                  disabled={generatingAI}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:bg-gray-400 text-sm"
                >
                  {generatingAI ? '⚙️ Generating...' : '🤖 Generate AI Descriptions'}
                </button>
              </div>

              {/* Primary Keys */}
              {selectedTableData.primary_keys.length > 0 && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-medium text-gray-700">Primary Keys:</span>
                  {selectedTableData.primary_keys.map((pk) => (
                    <span key={pk} className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded">
                      {pk}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Columns */}
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden mb-6">
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                <h3 className="font-semibold text-gray-900">Columns</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Column Name
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Data Type
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Type
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Aggregation
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {selectedTableData.columns.map((col) => (
                      <tr key={col.name} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="font-medium text-gray-900">{col.name}</div>
                          {col.display_name && col.display_name !== col.name && (
                            <div className="text-xs text-gray-500">{col.display_name}</div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <code className="bg-gray-100 px-2 py-1 rounded">{col.data_type}</code>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className={`px-2 py-1 rounded-full text-xs font-medium ${
                              col.is_measure
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-purple-100 text-purple-800'
                            }`}
                          >
                            {col.is_measure ? 'Measure' : 'Dimension'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {col.default_aggregation || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Relationships */}
            {selectedTable && getRelationshipsForTable(selectedTable).length > 0 && (
              <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                  <h3 className="font-semibold text-gray-900">Relationships</h3>
                </div>
                <div className="p-6 space-y-3">
                  {getRelationshipsForTable(selectedTable).map((rel, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex-1">
                        <span className="font-medium text-gray-900">
                          {rel.from_table}.{rel.from_column}
                        </span>
                      </div>
                      <div className="text-center">
                        <span className="px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full text-xs font-medium">
                          {rel.cardinality}
                        </span>
                      </div>
                      <div className="flex-1 text-right">
                        <span className="font-medium text-gray-900">
                          {rel.to_table}.{rel.to_column}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center">
            <p className="text-gray-500">Select a table to view details</p>
          </div>
        )}
      </div>
      </div>
    </div>
  );
};

export default SchemaExplorer;
