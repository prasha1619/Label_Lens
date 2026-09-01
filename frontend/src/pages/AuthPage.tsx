import React, { useState, useRef } from 'react';
import {
  ArrowRight,
  Camera,
  CheckCircle2,
  LockKeyhole,
  Mail,
  RotateCcw,
  Trash2,
  UploadCloud,
  UserRound,
  X,
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { authService } from '../services/authService';
import logo from '../assets/labellens-logo.png';

export const AuthPage: React.FC = () => {
  const { login, register, setUser } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [registerStep, setRegisterStep] = useState<1 | 2>(1);
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    confirm_password: '',
    organization: '',
  });
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [key]: e.target.value });
  };

  const handleStep1Submit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.confirm_password) {
      setError('Passwords do not match');
      return;
    }
    if (form.password.length < 8 || !/[A-Za-z]/.test(form.password) || !/[0-9]/.test(form.password)) {
      setError('Password must be at least 8 characters and include both letters and numbers.');
      return;
    }

    // Advance to Step 2: Optional Profile Photo
    setRegisterStep(2);
  };

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      setError('Invalid format. Please select a JPG, JPEG, PNG, or WEBP image.');
      return;
    }

    const maxMb = 3;
    if (file.size > maxMb * 1024 * 1024) {
      setError(`Profile photo must be less than ${maxMb}MB.`);
      return;
    }

    setError('');
    setPhotoFile(file);
    setPhotoPreview(URL.createObjectURL(file));
  };

  const completeRegistration = async (includePhoto: boolean) => {
    setError('');
    setBusy(true);
    try {
      // 1. Register account in backend
      const res = await authService.register(form);
      let currentUser = res.user;

      // 2. Upload optional photo if selected
      if (includePhoto && photoFile) {
        try {
          const photoRes = await authService.uploadPhoto(photoFile);
          currentUser = photoRes.user;
        } catch (photoErr) {
          console.warn('Photo upload failed after registration:', photoErr);
        }
      }

      setUser(currentUser);
    } catch (e: any) {
      setError(e.message || 'Registration failed. Please try again.');
      setBusy(false);
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await login(form.email, form.password);
    } catch (e: any) {
      setError(e.message || 'Invalid email or password.');
      setBusy(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#080c1d] px-4 py-10 flex items-center justify-center animate-fadeIn">
      <section className="w-full max-w-md overflow-hidden rounded-3xl border border-[#263765] bg-[#0d1430] shadow-2xl">
        {/* Header */}
        <div className="bg-gradient-to-br from-[#142653] to-[#0d1430] px-8 py-7 text-center border-b border-[#1c2a4f]">
          <img
            src={logo}
            alt="LabelLens"
            className="mx-auto h-20 w-20 rounded-2xl object-contain ring-2 ring-emerald-400/30 shadow-lg p-1.5 bg-[#091026]"
          />
          <h1 className="mt-4 text-2xl font-extrabold text-white tracking-tight">
            {mode === 'login'
              ? 'Welcome back'
              : registerStep === 1
              ? 'Create Inspector Account'
              : 'Profile Photo Setup'}
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            {mode === 'login'
              ? 'Sign in to access Legal Metrology audits'
              : registerStep === 1
              ? 'Step 1 of 2: Inspector Credentials'
              : 'Step 2 of 2: Optional Photo Upload'}
          </p>
        </div>

        {/* Login Form */}
        {mode === 'login' && (
          <form onSubmit={handleLoginSubmit} className="space-y-4 p-6 sm:p-8">
            <label className="block text-xs font-semibold text-slate-300">
              Email Address
              <div className="relative mt-1">
                <Mail className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
                <input
                  type="email"
                  value={form.email}
                  onChange={set('email')}
                  required
                  className="auth-input pl-10"
                  placeholder="inspector@labellens.gov.in"
                />
              </div>
            </label>

            <label className="block text-xs font-semibold text-slate-300">
              Password
              <div className="relative mt-1">
                <LockKeyhole className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
                <input
                  type="password"
                  value={form.password}
                  onChange={set('password')}
                  required
                  className="auth-input pl-10"
                  placeholder="••••••••"
                />
              </div>
            </label>

            {error && (
              <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-200">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={busy}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 py-3 text-sm font-bold text-white shadow-lg shadow-emerald-700/20 hover:from-emerald-500 hover:to-teal-400 disabled:opacity-60 transition-all"
            >
              {busy ? 'Verifying session…' : 'Sign In'}
              <ArrowRight className="h-4 w-4" />
            </button>

            <p className="text-center text-xs text-slate-400 pt-2">
              Don't have an account?{' '}
              <button
                type="button"
                onClick={() => {
                  setMode('register');
                  setRegisterStep(1);
                  setError('');
                }}
                className="font-bold text-emerald-400 hover:text-emerald-300"
              >
                Create account
              </button>
            </p>
          </form>
        )}

        {/* Register Step 1: Account Information */}
        {mode === 'register' && registerStep === 1 && (
          <form onSubmit={handleStep1Submit} className="space-y-4 p-6 sm:p-8">
            <label className="block text-xs font-semibold text-slate-300">
              Full Name
              <div className="relative mt-1">
                <UserRound className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
                <input
                  value={form.full_name}
                  onChange={set('full_name')}
                  required
                  minLength={2}
                  className="auth-input pl-10"
                  placeholder="e.g. Rahul Sharma"
                />
              </div>
            </label>

            <label className="block text-xs font-semibold text-slate-300">
              Email Address
              <div className="relative mt-1">
                <Mail className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
                <input
                  type="email"
                  value={form.email}
                  onChange={set('email')}
                  required
                  className="auth-input pl-10"
                  placeholder="rahul.sharma@gov.in"
                />
              </div>
            </label>

            <label className="block text-xs font-semibold text-slate-300">
              Organization <span className="text-slate-500 font-normal">(optional)</span>
              <input
                value={form.organization}
                onChange={set('organization')}
                className="auth-input mt-1"
                placeholder="Department of Legal Metrology"
              />
            </label>

            <label className="block text-xs font-semibold text-slate-300">
              Password
              <div className="relative mt-1">
                <LockKeyhole className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
                <input
                  type="password"
                  value={form.password}
                  onChange={set('password')}
                  required
                  minLength={8}
                  className="auth-input pl-10"
                  placeholder="••••••••"
                />
              </div>
              <span className="mt-1 block text-[10px] text-slate-500">
                At least 8 characters with letters & numbers.
              </span>
            </label>

            <label className="block text-xs font-semibold text-slate-300">
              Confirm Password
              <input
                type="password"
                value={form.confirm_password}
                onChange={set('confirm_password')}
                required
                className="auth-input mt-1"
                placeholder="••••••••"
              />
            </label>

            {error && (
              <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-200">
                {error}
              </p>
            )}

            <button
              type="submit"
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 py-3 text-sm font-bold text-white shadow-lg shadow-emerald-700/20 hover:from-emerald-500 hover:to-teal-400 transition-all"
            >
              Next: Profile Setup
              <ArrowRight className="h-4 w-4" />
            </button>

            <p className="text-center text-xs text-slate-400 pt-1">
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => {
                  setMode('login');
                  setError('');
                }}
                className="font-bold text-emerald-400 hover:text-emerald-300"
              >
                Sign in
              </button>
            </p>
          </form>
        )}

        {/* Register Step 2: Optional Profile Photo */}
        {mode === 'register' && registerStep === 2 && (
          <div className="space-y-5 p-6 sm:p-8">
            <div className="text-center space-y-2">
              <h3 className="text-base font-bold text-white">
                Would you like to upload a profile photo?
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Add an inspector photo or official badge. This is completely{' '}
                <strong className="text-emerald-400">optional</strong> and can be updated anytime.
              </p>
            </div>

            {/* Hidden File Input */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/jpg,image/png,image/webp"
              className="hidden"
              onChange={handlePhotoSelect}
            />

            {/* Preview Box or Placeholder */}
            <div className="flex flex-col items-center justify-center p-5 rounded-2xl border-2 border-dashed border-[#23345d] bg-[#090f24] space-y-3">
              {photoPreview ? (
                <div className="relative">
                  <img
                    src={photoPreview}
                    alt="Preview"
                    className="h-28 w-28 rounded-2xl object-cover ring-4 ring-emerald-500/40 shadow-xl"
                  />
                  <span className="absolute -bottom-1 -right-1 bg-emerald-500 text-white rounded-full p-1 shadow-md">
                    <CheckCircle2 className="h-4 w-4" />
                  </span>
                </div>
              ) : (
                <div className="flex h-24 w-24 items-center justify-center rounded-2xl bg-gradient-to-tr from-emerald-600/30 to-teal-500/20 border border-emerald-500/30 text-emerald-400">
                  <Camera className="h-10 w-10 stroke-[1.5]" />
                </div>
              )}

              {photoPreview ? (
                <div className="text-center space-y-1">
                  <p className="text-xs font-bold text-slate-200">{photoFile?.name}</p>
                  <p className="text-[10px] text-slate-400">
                    {(photoFile?.size ? photoFile.size / (1024 * 1024) : 0).toFixed(2)} MB &middot; Ready to save
                  </p>
                </div>
              ) : (
                <p className="text-xs text-slate-400 text-center">
                  Supports JPG, JPEG, PNG, WEBP (Max 3MB)
                </p>
              )}

              {/* Photo selection controls */}
              {photoPreview ? (
                <div className="flex items-center gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="inline-flex items-center gap-1.5 rounded-xl bg-slate-800 border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition-all"
                  >
                    <RotateCcw className="h-3 w-3" />
                    Change Photo
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setPhotoFile(null);
                      setPhotoPreview(null);
                    }}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-500/20 transition-all"
                  >
                    <Trash2 className="h-3 w-3" />
                    Remove
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 px-5 py-2.5 text-xs font-bold text-white shadow-md hover:from-emerald-500 hover:to-teal-400 transition-all"
                >
                  <UploadCloud className="h-4 w-4" />
                  Upload Photo
                </button>
              )}
            </div>

            {error && (
              <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-200">
                {error}
              </p>
            )}

            {/* Action Buttons: Save Photo vs Skip */}
            <div className="space-y-2 pt-1">
              {photoPreview ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => completeRegistration(true)}
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 py-3 text-sm font-bold text-white shadow-lg shadow-emerald-700/20 hover:from-emerald-500 hover:to-teal-400 disabled:opacity-60 transition-all"
                >
                  {busy ? 'Saving profile…' : 'Save & Complete Registration'}
                  <ArrowRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => completeRegistration(false)}
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-800 border border-slate-700 py-3 text-sm font-bold text-slate-200 hover:bg-slate-700 hover:text-white disabled:opacity-60 transition-all"
                >
                  {busy ? 'Creating account…' : 'Skip for now & Create Account'}
                  <ArrowRight className="h-4 w-4" />
                </button>
              )}

              <button
                type="button"
                disabled={busy}
                onClick={() => setRegisterStep(1)}
                className="w-full text-center text-xs text-slate-400 hover:text-slate-200 py-1"
              >
                &larr; Back to credentials
              </button>
            </div>
          </div>
        )}
      </section>
    </main>
  );
};

