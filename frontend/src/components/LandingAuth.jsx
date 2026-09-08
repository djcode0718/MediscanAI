import React, { useState } from 'react';
import { Shield, Sparkles, Heart, Activity, ArrowRight, Lock, Mail, User, Sun, Moon } from 'lucide-react';
import { API_ENDPOINTS } from '../config/api';

export default function LandingAuth({ onLogin, theme, toggleTheme }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password || (isSignUp && !name)) {
      setError('Please fill in all fields.');
      return;
    }
    setError('');
    setIsSubmitting(true);

    try {
      const endpoint = isSignUp 
        ? API_ENDPOINTS.AUTH_REGISTER 
        : API_ENDPOINTS.AUTH_LOGIN;

      const payload = isSignUp
        ? { email, password, full_name: name }
        : { email, password };

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        let msg = 'Authentication failed. Please check your credentials.';
        if (data.detail) {
          if (Array.isArray(data.detail)) {
            msg = data.detail.map(d => d.msg || d).join(', ');
          } else if (typeof data.detail === 'string') {
            msg = data.detail;
          }
        }
        setError(msg);
        return;
      }

      // Success: pass user & access_token to parent
      onLogin(data.user, data.access_token);
    } catch (err) {
      console.error('Auth request error:', err);
      setError('Unable to connect to the backend authentication server. Ensure the backend is running.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100 transition-colors duration-300 font-sans relative">
      {/* Floating Theme Toggle Switch */}
      <button
        onClick={toggleTheme}
        className="absolute top-6 right-6 z-50 p-2.5 rounded-xl bg-white hover:bg-slate-100 border border-slate-200 text-slate-600 hover:text-slate-900 dark:bg-slate-900 dark:hover:bg-slate-800 dark:border-slate-800 dark:text-slate-300 dark:hover:text-white transition-all cursor-pointer shadow-sm"
        aria-label="Toggle theme"
      >
        {theme === 'dark' ? <Sun className="w-4.5 h-4.5 text-teal-400" /> : <Moon className="w-4.5 h-4.5" />}
      </button>
      {/* Left panel - Product Showcases */}
      <div className="w-full md:w-1/2 bg-gradient-to-br from-teal-900 via-clinical-950 to-slate-950 text-white flex flex-col justify-between p-8 md:p-16 relative overflow-hidden">
        {/* Decorative background grid */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f766e0a_1px,transparent_1px),linear-gradient(to_bottom,#0f766e0a_1px,transparent_1px)] bg-[size:4rem_4rem]"></div>
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl"></div>

        {/* Brand Header */}
        <div className="relative z-10 flex items-center space-x-2.5">
          <div className="w-10 h-10 rounded-xl bg-teal-500 flex items-center justify-center shadow-lg shadow-teal-500/20">
            <Heart className="w-5.5 h-5.5 text-white fill-white/10" />
          </div>
          <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-teal-100 to-white bg-clip-text text-transparent">
            MediScanAI
          </span>
        </div>

        {/* Hero Concept */}
        <div className="relative z-10 my-auto py-12 md:py-0">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/20 text-teal-300 text-xs font-medium mb-6">
            <Sparkles className="w-3.5 h-3.5" />
            <span>100% Local Privacy-First Health Assistant</span>
          </div>
          
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight leading-tight mb-6">
            Understand your <br />
            <span className="bg-gradient-to-r from-teal-300 via-teal-200 to-emerald-300 bg-clip-text text-transparent">
              medicines & symptoms
            </span>
          </h1>
          
          <p className="text-slate-300 text-lg max-w-md leading-relaxed mb-8">
            Analyze symptom logs, medicine label images, and voice recordings locally on your device. Cross-reference data to verify suitability and discover safe alternatives instantly.
          </p>

          {/* Key Value Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg">
            <div className="p-4 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm">
              <Shield className="w-6 h-6 text-teal-400 mb-2" />
              <h3 className="font-semibold text-white text-sm mb-1">Device-Local Processing</h3>
              <p className="text-slate-400 text-xs leading-relaxed">Whisper, PaddleOCR, and local LLMs guarantee your health query never leaves your device.</p>
            </div>
            <div className="p-4 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm">
              <Activity className="w-6 h-6 text-emerald-400 mb-2" />
              <h3 className="font-semibold text-white text-sm mb-1">Vector Search Grounding</h3>
              <p className="text-slate-400 text-xs leading-relaxed">RAG verification ensures safety suggestions are locked strictly to official drug databases.</p>
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="relative z-10 text-xs text-slate-400">
          © {new Date().getFullYear()} MediScanAI. Educational Resource Only. Not replacing professional diagnosis.
        </div>
      </div>

      {/* Right panel - Forms */}
      <div className="w-full md:w-1/2 flex items-center justify-center p-8 md:p-16 bg-slate-50 dark:bg-slate-950">
        <div className="w-full max-w-md animate-fade-in">
          {/* Header tabs */}
          <div className="flex border-b border-slate-200 dark:border-slate-800 mb-8">
            <button
              onClick={() => { setIsSignUp(false); setError(''); }}
              className={`pb-3 text-sm font-semibold border-b-2 transition-all px-4 ${
                !isSignUp
                  ? 'border-teal-500 text-teal-600 dark:text-teal-400'
                  : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => { setIsSignUp(true); setError(''); }}
              className={`pb-3 text-sm font-semibold border-b-2 transition-all px-4 ${
                isSignUp
                  ? 'border-teal-500 text-teal-600 dark:text-teal-400'
                  : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Form */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-8 rounded-2xl shadow-sm">
            <h2 className="text-2xl font-bold mb-1 tracking-tight text-slate-900 dark:text-white">
              {isSignUp ? 'Get started today' : 'Welcome back'}
            </h2>
            <p className="text-slate-500 dark:text-slate-400 text-sm mb-6">
              {isSignUp ? 'Enter your details to register.' : 'Access your secure local health dashboard.'}
            </p>

            {error && (
              <div className="p-3 mb-4 text-xs font-medium text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/30 rounded-lg">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {isSignUp && (
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                    Full Name
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-3.5 w-4.5 h-4.5 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Jane Doe"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl py-3 pl-10 pr-4 text-sm outline-none focus:border-teal-500 transition-colors"
                      required={isSignUp}
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3.5 w-4.5 h-4.5 text-slate-400" />
                  <input
                    type="email"
                    placeholder="jane.doe@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl py-3 pl-10 pr-4 text-sm outline-none focus:border-teal-500 transition-colors"
                    required
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    Password
                  </label>
                  {!isSignUp && (
                    <a href="#forgot" className="text-xs text-teal-600 dark:text-teal-400 hover:underline">
                      Forgot?
                    </a>
                  )}
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-3.5 w-4.5 h-4.5 text-slate-400" />
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl py-3 pl-10 pr-4 text-sm outline-none focus:border-teal-500 transition-colors"
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-teal-600 hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded-xl transition-all shadow-md shadow-teal-600/10 flex items-center justify-center space-x-1 cursor-pointer"
              >
                <span>
                  {isSubmitting
                    ? (isSignUp ? 'Creating Account...' : 'Signing In...')
                    : (isSignUp ? 'Create Account' : 'Sign In')}
                </span>
                {!isSubmitting && <ArrowRight className="w-4 h-4" />}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
