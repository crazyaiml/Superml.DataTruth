import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config';
import { Plus, Save, Trash2, Calculator } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface Field {
  name: string;
  display_name: string;
  description: string;
  data_type: string;
  is_measure: boolean;
  default_aggregation: string;
  is_custom: boolean;
  formula?: string;
}

const SemanticLayer: React.FC = () => {
  const [connections, setConnections] = useState<any[]>([]);
  const [selectedConnection, setSelectedConnection] = useState<string>('');
  const [tables, setTables] = useState<string[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [fields, setFields] = useState<Field[]>([]);
  const [showAddCustomField, setShowAddCustomField] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const [newCustomField, setNewCustomField] = useState({
    name: '',
    display_name: '',
    description: '',
    formula: '',
    is_measure: true,
    default_aggregation: 'SUM'
  });

  const { token } = useAuth();

  // Load connections only once when token is available
  useEffect(() => {
    if (token && connections.length === 0) {
      loadConnections();
    }
  }, [token]);

  // Load tables when connection changes
  useEffect(() => {
    if (selectedConnection && token) {
      // Clear previous connection's data
      setTables([]);
      setSelectedTable('');
      setFields([]);
      loadTables();
    }
  }, [selectedConnection]);

  // Load fields when table or connection changes
  useEffect(() => {
    if (selectedTable && selectedConnection && token) {
      loadFields();
    } else if (!selectedTable) {
      // Clear fields if no table selected
      setFields([]);
    }
  }, [selectedTable, selectedConnection]);

  const loadConnections = async () => {
    if (!token) return;
    try {
      const response = await axios.get(`${API_URL}/api/v1/connections`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const conns = response.data.connections || [];
      setConnections(conns);
      if (conns.length > 0 && !selectedConnection) {
        setSelectedConnection(conns[0].id);
      }
    } catch (err) {
      console.error('Failed to load connections:', err);
    }
  };

  const loadTables = async () => {
    if (!token || !selectedConnection) return;
    try {
      setLoading(true);
      const response = await axios.post(
        `${API_URL}/api/v1/connections/${selectedConnection}/discover`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const tableNames = Object.keys(response.data.tables || {});
      setTables(tableNames);
      // Always set first table when tables are loaded for new connection
      if (tableNames.length > 0) {
        setSelectedTable(tableNames[0]);
      }
    } catch (err: any) {
      console.error('Failed to load tables:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadFields = async () => {
    if (!token || !selectedConnection || !selectedTable) return;
    try {
      setLoading(true);
      
      // First, get the raw schema columns
      const schemaResponse = await axios.get(
        `${API_URL}/api/v1/connections/${selectedConnection}/schema/${selectedTable}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Then, try to load saved field mappings for each column
      const tableFields: Field[] = [];
      
      for (const col of schemaResponse.data.columns) {
        try {
          // Try to fetch saved field mapping
          const mappingResponse = await axios.get(
            `${API_URL}/api/v1/fieldmap/${selectedTable}/${col.name}?connection_id=${selectedConnection}`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          
          const mapping = mappingResponse.data;
          
          // Use saved mapping if available, otherwise use schema defaults
          tableFields.push({
            name: col.name,
            display_name: mapping.display_name || col.display_name || col.name,
            description: mapping.description || col.description || '',
            data_type: col.data_type,
            is_measure: mapping.is_measure !== undefined ? mapping.is_measure : col.is_measure,
            default_aggregation: mapping.default_aggregation || col.default_aggregation || (col.is_measure ? 'SUM' : 'NONE'),
            is_custom: mapping.is_custom || false,
            formula: mapping.formula || undefined
          });
        } catch (err) {
          // If no saved mapping, use schema defaults
          tableFields.push({
            name: col.name,
            display_name: col.display_name || col.name,
            description: col.description || '',
            data_type: col.data_type,
            is_measure: col.is_measure,
            default_aggregation: col.default_aggregation || (col.is_measure ? 'SUM' : 'NONE'),
            is_custom: false
          });
        }
      }
      
      // Load calculated metrics from database for this table
      try {
        const metricsResponse = await axios.get(
          `${API_URL}/api/v1/calculated-metrics?connection_id=${selectedConnection}&base_table=${selectedTable}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        
        // Add calculated metrics as custom fields
        const metrics = metricsResponse.data.metrics || [];
        for (const metric of metrics) {
          tableFields.push({
            name: metric.metric_name,
            display_name: metric.display_name,
            description: metric.description || '',
            data_type: 'CALCULATED',
            is_measure: true,
            default_aggregation: metric.aggregation || 'calculated',
            is_custom: true,
            formula: metric.formula
          });
        }
      } catch (err) {
        console.log('No calculated metrics found for this table');
      }
      
      setFields(tableFields);
    } catch (err: any) {
      console.error('Failed to load fields:', err);
      setMessage({ type: 'error', text: 'Failed to load fields' });
    } finally {
      setLoading(false);
    }
  };

  const updateField = (fieldName: string, updates: Partial<Field>) => {
    setFields(prev => prev.map(f => 
      f.name === fieldName ? { ...f, ...updates } : f
    ));
  };

  const addCustomField = () => {
    if (!newCustomField.name || !newCustomField.formula) {
      setMessage({ type: 'error', text: 'Name and formula are required' });
      return;
    }

    const customField: Field = {
      name: newCustomField.name,
      display_name: newCustomField.display_name || newCustomField.name,
      description: newCustomField.description,
      data_type: 'CALCULATED',
      is_measure: newCustomField.is_measure,
      default_aggregation: newCustomField.default_aggregation,
      is_custom: true,
      formula: newCustomField.formula
    };

    setFields(prev => [...prev, customField]);
    setShowAddCustomField(false);
    setNewCustomField({
      name: '',
      display_name: '',
      description: '',
      formula: '',
      is_measure: true,
      default_aggregation: 'SUM'
    });
    setMessage({ type: 'success', text: 'Custom field added! Remember to save changes.' });
  };

  const deleteCustomField = async (fieldName: string) => {
    if (!confirm(`Delete custom field "${fieldName}"?`)) return;
    
    try {
      // Remove from UI immediately
      setFields(prev => prev.filter(f => f.name !== fieldName));
      
      // If it's a calculated metric, also delete from database
      if (token && selectedConnection) {
        try {
          await axios.delete(
            `${API_URL}/api/v1/calculated-metrics/${fieldName}?connection_id=${selectedConnection}`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          setMessage({ type: 'success', text: 'Custom field deleted from database!' });
        } catch (err) {
          // If delete fails, it might not be in database yet
          console.log('Metric not in database or delete failed:', err);
          setMessage({ type: 'success', text: 'Custom field removed!' });
        }
      } else {
        setMessage({ type: 'success', text: 'Custom field removed!' });
      }
    } catch (err) {
      console.error('Failed to delete custom field:', err);
      setMessage({ type: 'error', text: 'Failed to delete custom field' });
    }
  };

  const saveSemanticLayer = async () => {
    if (!token || !selectedConnection || !selectedTable) return;
    
    try {
      setSaving(true);
      
      // Save field mappings
      for (let i = 0; i < fields.length; i++) {
        const field = fields[i];
        await axios.post(
          `${API_URL}/api/v1/fieldmap/save`,
          {
            connection_id: selectedConnection,
            table_name: selectedTable,
            field_name: field.name,
            display_name: field.display_name,
            description: field.description,
            default_aggregation: field.default_aggregation,
            is_custom: field.is_custom,
            formula: field.formula
          },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        
        // Small delay to respect rate limits (except for last field)
        if (i < fields.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }
      
      setMessage({ type: 'success', text: 'Semantic layer saved successfully!' });
      setTimeout(() => setMessage(null), 3000);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to save' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Semantic Layer</h2>
            <p className="text-sm text-gray-500 mt-1">
              Define business-friendly names, descriptions, and calculated fields
            </p>
          </div>
          <button
            onClick={saveSemanticLayer}
            disabled={saving || !selectedTable}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:bg-gray-400 flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save All Changes'}
          </button>
        </div>

        {/* Selectors */}
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Connection</label>
            <select
              value={selectedConnection}
              onChange={(e) => setSelectedConnection(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-indigo-500"
            >
              {connections.map((conn) => (
                <option key={conn.id} value={conn.id}>{conn.name}</option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Table</label>
            <select
              value={selectedTable}
              onChange={(e) => setSelectedTable(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-indigo-500"
            >
              {tables.map((table) => (
                <option key={table} value={table}>{table}</option>
              ))}
            </select>
          </div>
        </div>

        {message && (
          <div className={`mt-4 p-3 rounded-md ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
            {message.text}
          </div>
        )}
      </div>

      {/* Fields Table */}
      <div className="flex-1 overflow-auto p-6">
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            <p className="mt-2 text-gray-600">Loading fields...</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            {/* Header with Add Button */}
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
              <h3 className="font-semibold text-gray-900">
                Fields ({fields.length})
              </h3>
              <button
                onClick={() => setShowAddCustomField(true)}
                className="px-3 py-1.5 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Calculated Field
              </button>
            </div>

            {/* Fields Table */}
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Field Name</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Display Name</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Aggregation</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Formula</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {fields.map((field) => (
                    <tr key={field.name} className={field.is_custom ? 'bg-purple-50' : ''}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {field.is_custom && <Calculator className="w-4 h-4 text-purple-600" />}
                          <code className="text-sm font-medium text-gray-900">{field.name}</code>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <input
                          type="text"
                          value={field.display_name}
                          onChange={(e) => updateField(field.name, { display_name: e.target.value })}
                          className="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:ring-1 focus:ring-indigo-500"
                        />
                      </td>
                      <td className="px-6 py-4">
                        <input
                          type="text"
                          value={field.description}
                          onChange={(e) => updateField(field.name, { description: e.target.value })}
                          placeholder="Add description..."
                          className="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:ring-1 focus:ring-indigo-500"
                        />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <select
                          value={field.is_measure ? 'measure' : 'dimension'}
                          onChange={(e) => updateField(field.name, { is_measure: e.target.value === 'measure' })}
                          className="px-2 py-1 border border-gray-300 rounded text-sm"
                        >
                          <option value="measure">Measure</option>
                          <option value="dimension">Dimension</option>
                        </select>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <select
                          value={field.default_aggregation}
                          onChange={(e) => updateField(field.name, { default_aggregation: e.target.value })}
                          disabled={!field.is_measure}
                          className="px-2 py-1 border border-gray-300 rounded text-sm disabled:bg-gray-100"
                        >
                          <option value="NONE">None</option>
                          <option value="SUM">SUM</option>
                          <option value="AVG">AVG</option>
                          <option value="COUNT">COUNT</option>
                          <option value="MIN">MIN</option>
                          <option value="MAX">MAX</option>
                        </select>
                      </td>
                      <td className="px-6 py-4">
                        {field.is_custom ? (
                          <code className="text-xs bg-gray-100 px-2 py-1 rounded">{field.formula}</code>
                        ) : (
                          <span className="text-xs text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {field.is_custom && (
                          <button
                            onClick={() => deleteCustomField(field.name)}
                            className="text-red-600 hover:text-red-900"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Add Custom Field Modal */}
      {showAddCustomField && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Add Calculated Field</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Field Name *</label>
                <input
                  type="text"
                  value={newCustomField.name}
                  onChange={(e) => setNewCustomField(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., total_revenue"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
                <input
                  type="text"
                  value={newCustomField.display_name}
                  onChange={(e) => setNewCustomField(prev => ({ ...prev, display_name: e.target.value }))}
                  placeholder="e.g., Total Revenue"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <input
                  type="text"
                  value={newCustomField.description}
                  onChange={(e) => setNewCustomField(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="e.g., Sum of all transaction amounts"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Formula *</label>
                <input
                  type="text"
                  value={newCustomField.formula}
                  onChange={(e) => setNewCustomField(prev => ({ ...prev, formula: e.target.value }))}
                  placeholder="e.g., SUM(amount) or amount - cost"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Examples: SUM(revenue), amount - cost, ROUND(price * 1.1, 2)
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                  <select
                    value={newCustomField.is_measure ? 'measure' : 'dimension'}
                    onChange={(e) => setNewCustomField(prev => ({ 
                      ...prev, 
                      is_measure: e.target.value === 'measure' 
                    }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  >
                    <option value="measure">Measure (Numeric)</option>
                    <option value="dimension">Dimension (Categorical)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Default Aggregation</label>
                  <select
                    value={newCustomField.default_aggregation}
                    onChange={(e) => setNewCustomField(prev => ({ 
                      ...prev, 
                      default_aggregation: e.target.value 
                    }))}
                    disabled={!newCustomField.is_measure}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-100"
                  >
                    <option value="SUM">SUM</option>
                    <option value="AVG">AVG</option>
                    <option value="COUNT">COUNT</option>
                    <option value="MIN">MIN</option>
                    <option value="MAX">MAX</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="mt-6 flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowAddCustomField(false);
                  setNewCustomField({
                    name: '',
                    display_name: '',
                    description: '',
                    formula: '',
                    is_measure: true,
                    default_aggregation: 'SUM'
                  });
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={addCustomField}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                Add Field
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SemanticLayer;
