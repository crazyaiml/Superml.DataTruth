import React, { useState, useEffect } from 'react';
import { 
  CheckCircle, 
  AlertCircle, 
  Database, 
  Key, 
  User, 
  Rocket,
  Loader2,
  ChevronRight,
  ChevronLeft
} from 'lucide-react';
import { API_URL } from '../../config';

interface SetupStatus {
  is_configured: boolean;
  needs_setup: boolean;
  setup_step?: string;
  error?: string;
}

interface DatabaseConfig {
  use_docker_db: boolean;  // NEW: Choice flag
  host: string;
  port: number;
  name: string;
  user: string;
  password: string;
  admin_user: string;
  admin_password: string;
}

interface OpenAIConfig {
  api_key: string;
  model: string;
  temperature: number;
}

interface AdminUserConfig {
  username: string;
  password: string;
  email?: string;
  full_name?: string;
}

interface SetupData {
  database: DatabaseConfig;
  openai: OpenAIConfig;
  admin_user: AdminUserConfig;
  app_name: string;
  app_url?: string;
}

const SetupWizard: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  
  const [setupData, setSetupData] = useState<SetupData>({
    database: {
      use_docker_db: true,  // Default to Docker database
      host: 'postgres',
      port: 5432,
      name: 'datatruth_internal',
      user: 'datatruth_app',
      password: '',
      admin_user: 'datatruth_admin',
      admin_password: ''
    },
    openai: {
      api_key: '',
      model: 'gpt-4o-mini',
      temperature: 0.7
    },
    admin_user: {
      username: 'admin',
      password: '',
      email: '',
      full_name: ''
    },
    app_name: 'DataTruth',
    app_url: ''
  });

  const [testResults, setTestResults] = useState<{
    database?: any;
    openai?: any;
  }>({});

  useEffect(() => {
    checkSetupStatus();
  }, []);

  const checkSetupStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/api/setup/status`);
      const status: SetupStatus = await response.json();
      
      if (status.is_configured) {
        // Redirect to main app
        window.location.href = '/';
      }
    } catch (err) {
      console.error('Failed to check setup status:', err);
    }
  };

  const testDatabaseConnection = async () => {
    setTesting(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/api/setup/test-database`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(setupData.database)
      });
      
      const result = await response.json();
      setTestResults(prev => ({ ...prev, database: result }));
      
      if (!result.success) {
        setError(result.message || 'Database connection failed');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to test database connection');
    } finally {
      setTesting(false);
    }
  };

  const testOpenAIConnection = async () => {
    setTesting(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/api/setup/test-openai`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(setupData.openai)
      });
      
      const result = await response.json();
      setTestResults(prev => ({ ...prev, openai: result }));
      
      if (!result.success) {
        setError(result.message || 'OpenAI connection failed');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to test OpenAI connection');
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/api/setup/initialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(setupData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        // Handle various error formats
        const errorMessage = errorData.detail || 
                           errorData.message || 
                           (typeof errorData === 'string' ? errorData : 'Setup failed');
        throw new Error(errorMessage);
      }
      
      await response.json(); // Wait for response
      setSuccess(true);
      
      // Redirect after 3 seconds
      setTimeout(() => {
        window.location.href = '/';
      }, 3000);
    } catch (err: any) {
      // Properly handle error objects
      let errorMessage = 'Setup initialization failed';
      
      if (err.message) {
        errorMessage = err.message;
      } else if (typeof err === 'string') {
        errorMessage = err;
      } else if (err.detail) {
        errorMessage = err.detail;
      }
      
      setError(errorMessage);
      console.error('Setup error:', err);
    } finally {
      setLoading(false);
    }
  };

  const steps = [
    {
      title: 'Welcome',
      icon: Rocket,
      description: 'Welcome to DataTruth Setup'
    },
    {
      title: 'Database',
      icon: Database,
      description: 'Configure your PostgreSQL database'
    },
    {
      title: 'OpenAI',
      icon: Key,
      description: 'Connect your OpenAI API'
    },
    {
      title: 'Admin User',
      icon: User,
      description: 'Create your admin account'
    },
    {
      title: 'Complete',
      icon: CheckCircle,
      description: 'Review and finish setup'
    }
  ];

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="text-center space-y-6">
            <div className="w-24 h-24 bg-blue-100 rounded-full flex items-center justify-center mx-auto">
              <Rocket className="w-12 h-12 text-blue-600" />
            </div>
            <h2 className="text-3xl font-bold text-gray-900">Welcome to DataTruth</h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Let's get your AI-powered analytics platform up and running in just a few steps.
              This wizard will help you configure your database, OpenAI integration, and create your admin account.
            </p>
            <div className="grid grid-cols-3 gap-4 mt-8 max-w-3xl mx-auto">
              <div className="p-4 bg-gray-50 rounded-lg">
                <Database className="w-8 h-8 text-blue-600 mx-auto mb-2" />
                <h3 className="font-semibold text-gray-900">Database</h3>
                <p className="text-sm text-gray-600">PostgreSQL setup</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <Key className="w-8 h-8 text-blue-600 mx-auto mb-2" />
                <h3 className="font-semibold text-gray-900">OpenAI</h3>
                <p className="text-sm text-gray-600">AI integration</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <User className="w-8 h-8 text-blue-600 mx-auto mb-2" />
                <h3 className="font-semibold text-gray-900">Admin</h3>
                <p className="text-sm text-gray-600">Your account</p>
              </div>
            </div>
          </div>
        );

      case 1:
        return (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Database Configuration</h2>
              <p className="text-gray-600">Choose how you want to set up your database</p>
            </div>

            {/* Database Choice */}
            <div className="space-y-4">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Database Setup Option
              </label>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Option 1: Use Docker Database */}
                <button
                  type="button"
                  onClick={() => setSetupData({
                    ...setupData,
                    database: { ...setupData.database, use_docker_db: true }
                  })}
                  className={`p-6 border-2 rounded-lg text-left transition-all ${
                    setupData.database.use_docker_db
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5 ${
                      setupData.database.use_docker_db
                        ? 'border-blue-500 bg-blue-500'
                        : 'border-gray-300'
                    }`}>
                      {setupData.database.use_docker_db && (
                        <CheckCircle className="w-3 h-3 text-white" />
                      )}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900 mb-1">
                        Create New Database (Recommended)
                      </h3>
                      <p className="text-sm text-gray-600">
                        We'll automatically create and configure a PostgreSQL database for you. 
                        No setup required - just click next!
                      </p>
                      <div className="mt-3 flex items-center space-x-2 text-xs text-gray-500">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        <span>Fastest setup</span>
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        <span>Automatic configuration</span>
                      </div>
                    </div>
                  </div>
                </button>

                {/* Option 2: Use Existing Database */}
                <button
                  type="button"
                  onClick={() => setSetupData({
                    ...setupData,
                    database: { ...setupData.database, use_docker_db: false }
                  })}
                  className={`p-6 border-2 rounded-lg text-left transition-all ${
                    !setupData.database.use_docker_db
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5 ${
                      !setupData.database.use_docker_db
                        ? 'border-blue-500 bg-blue-500'
                        : 'border-gray-300'
                    }`}>
                      {!setupData.database.use_docker_db && (
                        <CheckCircle className="w-3 h-3 text-white" />
                      )}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900 mb-1">
                        Use Existing Database
                      </h3>
                      <p className="text-sm text-gray-600">
                        Connect to your own PostgreSQL database. 
                        You'll need to provide connection details.
                      </p>
                      <div className="mt-3 flex items-center space-x-2 text-xs text-gray-500">
                        <Database className="w-4 h-4 text-blue-500" />
                        <span>Full control</span>
                        <Database className="w-4 h-4 text-blue-500" />
                        <span>Existing infrastructure</span>
                      </div>
                    </div>
                  </div>
                </button>
              </div>
            </div>

            {/* Show database fields only if using existing database */}
            {!setupData.database.use_docker_db && (
              <>
                <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <div className="flex items-start space-x-2">
                    <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
                    <div className="text-sm text-yellow-800">
                      <p className="font-medium">Requirements for existing database:</p>
                      <ul className="mt-2 space-y-1 list-disc list-inside">
                        <li>PostgreSQL 12 or higher</li>
                        <li>Database must already exist</li>
                        <li>Admin user must have CREATE DATABASE and CREATE ROLE privileges</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Host
                    </label>
                    <input
                      type="text"
                      value={setupData.database.host}
                      onChange={(e) => setSetupData({
                        ...setupData,
                        database: { ...setupData.database, host: e.target.value }
                      })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="localhost"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Port
                    </label>
                    <input
                      type="number"
                      value={setupData.database.port}
                      onChange={(e) => setSetupData({
                        ...setupData,
                        database: { ...setupData.database, port: parseInt(e.target.value) }
                      })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Database Name
                    </label>
                    <input
                      type="text"
                      value={setupData.database.name}
                      onChange={(e) => setSetupData({
                        ...setupData,
                        database: { ...setupData.database, name: e.target.value }
                      })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      App User
                    </label>
                    <input
                      type="text"
                      value={setupData.database.user}
                      onChange={(e) => setSetupData({
                        ...setupData,
                        database: { ...setupData.database, user: e.target.value }
                      })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      App Password
                    </label>
                    <input
                      type="password"
                      value={setupData.database.password}
                      onChange={(e) => setSetupData({
                        ...setupData,
                        database: { ...setupData.database, password: e.target.value }
                      })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter strong password"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Admin User
                    </label>
                    <input
                      type="text"
                      value={setupData.database.admin_user}
                      onChange={(e) => setSetupData({
                        ...setupData,
                        database: { ...setupData.database, admin_user: e.target.value }
                      })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Admin Password
                    </label>
                    <input
                      type="password"
                      value={setupData.database.admin_password}
                      onChange={(e) => setSetupData({
                        ...setupData,
                        database: { ...setupData.database, admin_password: e.target.value }
                      })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter strong admin password"
                    />
                  </div>
                </div>

                <button
                  onClick={testDatabaseConnection}
                  disabled={testing || !setupData.database.admin_password}
                  className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  {testing ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Testing Connection...
                    </>
                  ) : (
                    'Test Database Connection'
                  )}
                </button>

                {testResults.database && (
                  <div className={`p-4 rounded-lg ${testResults.database.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                    <div className="flex items-start">
                      {testResults.database.success ? (
                        <CheckCircle className="w-5 h-5 text-green-600 mr-2 mt-0.5" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-red-600 mr-2 mt-0.5" />
                      )}
                      <div>
                        <p className={`font-medium ${testResults.database.success ? 'text-green-900' : 'text-red-900'}`}>
                          {testResults.database.message}
                        </p>
                        {testResults.database.version && (
                          <p className="text-sm text-gray-600 mt-1">
                            PostgreSQL Version: {testResults.database.version.split(' ')[1]}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Info message when using Docker database */}
            {setupData.database.use_docker_db && (
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-start space-x-2">
                  <CheckCircle className="w-5 h-5 text-blue-600 mt-0.5" />
                  <div className="text-sm text-blue-800">
                    <p className="font-medium">Using Managed Database</p>
                    <p className="mt-1">
                      We'll automatically set up a secure PostgreSQL database for you. 
                      Your database will be ready in seconds - just click "Next" to continue!
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">OpenAI Configuration</h2>
              <p className="text-gray-600">Connect your OpenAI API for AI-powered queries</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  API Key
                </label>
                <input
                  type="password"
                  value={setupData.openai.api_key}
                  onChange={(e) => setSetupData({
                    ...setupData,
                    openai: { ...setupData.openai, api_key: e.target.value }
                  })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="sk-..."
                />
                <p className="text-sm text-gray-500 mt-1">
                  Get your API key from <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">OpenAI Platform</a>
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Model
                </label>
                <select
                  value={setupData.openai.model}
                  onChange={(e) => setSetupData({
                    ...setupData,
                    openai: { ...setupData.openai, model: e.target.value }
                  })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="gpt-4o-mini">GPT-4o Mini (Recommended)</option>
                  <option value="gpt-4o">GPT-4o</option>
                  <option value="gpt-4-turbo">GPT-4 Turbo</option>
                  <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Temperature: {setupData.openai.temperature}
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={setupData.openai.temperature}
                  onChange={(e) => setSetupData({
                    ...setupData,
                    openai: { ...setupData.openai, temperature: parseFloat(e.target.value) }
                  })}
                  className="w-full"
                />
                <div className="flex justify-between text-sm text-gray-500">
                  <span>Precise (0.0)</span>
                  <span>Balanced (1.0)</span>
                  <span>Creative (2.0)</span>
                </div>
              </div>
            </div>

            <button
              onClick={testOpenAIConnection}
              disabled={testing || !setupData.openai.api_key}
              className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {testing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Testing API Key...
                </>
              ) : (
                'Test OpenAI Connection'
              )}
            </button>

            {testResults.openai && (
              <div className={`p-4 rounded-lg ${testResults.openai.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-start">
                  {testResults.openai.success ? (
                    <CheckCircle className="w-5 h-5 text-green-600 mr-2 mt-0.5" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-red-600 mr-2 mt-0.5" />
                  )}
                  <div>
                    <p className={`font-medium ${testResults.openai.success ? 'text-green-900' : 'text-red-900'}`}>
                      {testResults.openai.message}
                    </p>
                    {testResults.openai.model && (
                      <p className="text-sm text-gray-600 mt-1">
                        Model: {testResults.openai.model}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        );

      case 3:
        return (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Create Admin Account</h2>
              <p className="text-gray-600">Set up your administrator account</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Username *
                </label>
                <input
                  type="text"
                  value={setupData.admin_user.username}
                  onChange={(e) => setSetupData({
                    ...setupData,
                    admin_user: { ...setupData.admin_user, username: e.target.value }
                  })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="admin"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Password *
                </label>
                <input
                  type="password"
                  value={setupData.admin_user.password}
                  onChange={(e) => setSetupData({
                    ...setupData,
                    admin_user: { ...setupData.admin_user, password: e.target.value }
                  })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Enter strong password"
                />
                <p className="text-sm text-gray-500 mt-1">
                  Must be at least 8 characters with uppercase, lowercase, and numbers
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email
                </label>
                <input
                  type="email"
                  value={setupData.admin_user.email}
                  onChange={(e) => setSetupData({
                    ...setupData,
                    admin_user: { ...setupData.admin_user, email: e.target.value }
                  })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="admin@example.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Full Name
                </label>
                <input
                  type="text"
                  value={setupData.admin_user.full_name}
                  onChange={(e) => setSetupData({
                    ...setupData,
                    admin_user: { ...setupData.admin_user, full_name: e.target.value }
                  })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="John Doe"
                />
              </div>
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Review & Complete</h2>
              <p className="text-gray-600">Review your configuration and finish setup</p>
            </div>

            <div className="space-y-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-gray-900 mb-2 flex items-center">
                  <Database className="w-5 h-5 mr-2" />
                  Database
                </h3>
                <div className="text-sm text-gray-600 space-y-1">
                  <p>Host: {setupData.database.host}:{setupData.database.port}</p>
                  <p>Database: {setupData.database.name}</p>
                  <p>User: {setupData.database.user}</p>
                </div>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-gray-900 mb-2 flex items-center">
                  <Key className="w-5 h-5 mr-2" />
                  OpenAI
                </h3>
                <div className="text-sm text-gray-600 space-y-1">
                  <p>Model: {setupData.openai.model}</p>
                  <p>Temperature: {setupData.openai.temperature}</p>
                  <p>API Key: {setupData.openai.api_key.substring(0, 10)}...</p>
                </div>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-gray-900 mb-2 flex items-center">
                  <User className="w-5 h-5 mr-2" />
                  Admin User
                </h3>
                <div className="text-sm text-gray-600 space-y-1">
                  <p>Username: {setupData.admin_user.username}</p>
                  {setupData.admin_user.email && <p>Email: {setupData.admin_user.email}</p>}
                  {setupData.admin_user.full_name && <p>Name: {setupData.admin_user.full_name}</p>}
                </div>
              </div>
            </div>

            {success ? (
              <div className="p-6 bg-green-50 border border-green-200 rounded-lg text-center">
                <CheckCircle className="w-16 h-16 text-green-600 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-green-900 mb-2">Setup Complete!</h3>
                <p className="text-green-700">Redirecting to application...</p>
              </div>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={loading}
                className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center text-lg font-semibold"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Initializing Application...
                  </>
                ) : (
                  <>
                    <Rocket className="w-5 h-5 mr-2" />
                    Complete Setup
                  </>
                )}
              </button>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case 0:
        return true;
      case 1:
        // If using Docker database, allow proceeding without test
        // If using existing database, require successful connection test
        return setupData.database.use_docker_db || testResults.database?.success || false;
      case 2:
        return testResults.openai?.success || false;
      case 3:
        return setupData.admin_user.username && setupData.admin_user.password.length >= 8;
      case 4:
        return true;
      default:
        return false;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full p-8">
        {/* Progress Steps */}
        <div className="mb-8">
          <div className="flex justify-between items-center">
            {steps.map((step, index) => {
              const Icon = step.icon;
              const isActive = index === currentStep;
              const isCompleted = index < currentStep;
              
              return (
                <div key={index} className="flex items-center flex-1">
                  <div className={`flex items-center justify-center w-10 h-10 rounded-full ${
                    isActive ? 'bg-blue-600 text-white' :
                    isCompleted ? 'bg-green-600 text-white' :
                    'bg-gray-200 text-gray-600'
                  }`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  {index < steps.length - 1 && (
                    <div className={`flex-1 h-1 mx-2 ${
                      isCompleted ? 'bg-green-600' : 'bg-gray-200'
                    }`} />
                  )}
                </div>
              );
            })}
          </div>
          <div className="flex justify-between mt-2">
            {steps.map((step, index) => (
              <div key={index} className="flex-1 text-center">
                <p className={`text-xs font-medium ${
                  index === currentStep ? 'text-blue-600' :
                  index < currentStep ? 'text-green-600' :
                  'text-gray-500'
                }`}>
                  {step.title}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="mb-8 min-h-[400px]">
          {renderStepContent()}
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start">
              <AlertCircle className="w-5 h-5 text-red-600 mr-2 mt-0.5" />
              <p className="text-red-900">{error}</p>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between">
          <button
            onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
            disabled={currentStep === 0 || loading}
            className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Back
          </button>

          {currentStep < steps.length - 1 && (
            <button
              onClick={() => setCurrentStep(currentStep + 1)}
              disabled={!canProceed() || loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center"
            >
              Next
              <ChevronRight className="w-4 h-4 ml-1" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SetupWizard;
