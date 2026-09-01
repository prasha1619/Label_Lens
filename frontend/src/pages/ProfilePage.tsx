import React, { useState, useRef } from 'react';
import { Camera, Image as ImageIcon, KeyRound, Save, Trash2, UploadCloud, UserRound, X } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { authService } from '../services/authService';

export const ProfilePage: React.FC = () => {
  const { user, setUser, logout } = useAuth();
  const [name, setName] = useState(user?.full_name || '');
  const [organization, setOrganization] = useState(user?.organization || '');
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [isPhotoBusy, setIsPhotoBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate type
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      setMessage({ type: 'error', text: 'Invalid image format. Please select a JPG, JPEG, PNG, or WEBP file.' });
      return;
    }

    // Validate size (max 3MB)
    const maxMb = 3;
    if (file.size > maxMb * 1024 * 1024) {
      setMessage({ type: 'error', text: `File size exceeds ${maxMb}MB limit.` });
      return;
    }

    setPhotoFile(file);
    const url = URL.createObjectURL(file);
    setPhotoPreview(url);
    setMessage(null);
  };

  const handleSavePhoto = async () => {
    if (!photoFile) return;
    setIsPhotoBusy(true);
    setMessage(null);
    try {
      const res = await authService.uploadPhoto(photoFile);
      setUser(res.user);
      setPhotoFile(null);
      setPhotoPreview(null);
      setMessage({ type: 'success', text: 'Profile photo updated successfully.' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to upload profile photo.' });
    } finally {
      setIsPhotoBusy(false);
    }
  };

  const handleRemovePhoto = async () => {
    setIsPhotoBusy(true);
    setMessage(null);
    try {
      const res = await authService.removePhoto();
      setUser(res.user);
      setPhotoFile(null);
      setPhotoPreview(null);
      setMessage({ type: 'success', text: 'Profile photo removed.' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to remove profile photo.' });
    } finally {
      setIsPhotoBusy(false);
    }
  };

  const handleSaveDetails = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    try {
      const updated = await authService.update(name, organization);
      setUser(updated);
      setMessage({ type: 'success', text: 'Profile details updated successfully.' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to update profile.' });
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    try {
      const result = await authService.changePassword(current, next, confirm);
      setMessage({ type: 'success', text: result.message });
      setCurrent('');
      setNext('');
      setConfirm('');
      setTimeout(() => logout(), 1000);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to change password.' });
    }
  };

  const initials = user?.full_name
    ? user.full_name
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map((n) => n[0])
        .join('')
        .toUpperCase()
    : 'LM';

  return (
    <div className="mx-auto max-w-4xl space-y-6 animate-fadeIn pb-10">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Inspector Profile</h1>
        <p className="mt-1 text-sm text-slate-400">
          Manage your verified inspector profile, security credentials, and organization.
        </p>
      </div>

      {message && (
        <div
          className={`p-3.5 rounded-2xl border text-xs flex items-center justify-between ${
            message.type === 'success'
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
              : 'border-rose-500/30 bg-rose-500/10 text-rose-300'
          }`}
        >
          <span>{message.text}</span>
          <button onClick={() => setMessage(null)} className="p-1 hover:opacity-75">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Top Profile Photo Section */}
      <div className="rounded-3xl border border-[#1e2a4a] bg-[#0c1328] p-6 shadow-xl space-y-5">
        <h2 className="flex items-center gap-2 text-base font-bold text-white">
          <Camera className="h-4 w-4 text-emerald-400" />
          Inspector Profile Photo
        </h2>

        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
          {/* Avatar Preview */}
          <div className="relative shrink-0">
            {photoPreview ? (
              <img
                src={photoPreview}
                alt="Preview"
                className="h-24 w-24 rounded-3xl object-cover ring-4 ring-emerald-500/30 shadow-xl"
              />
            ) : user?.profile_photo_url ? (
              <img
                src={user.profile_photo_url}
                alt={user.full_name}
                className="h-24 w-24 rounded-3xl object-cover ring-4 ring-emerald-500/30 shadow-xl"
              />
            ) : (
              <div className="h-24 w-24 rounded-3xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white text-2xl font-black flex items-center justify-center ring-4 ring-emerald-500/30 shadow-xl">
                {initials}
              </div>
            )}
            <span className="absolute -bottom-1 -right-1 flex h-4 w-4">
              <span className="relative inline-flex rounded-full h-4 w-4 bg-emerald-500 ring-2 ring-[#0c1328]" />
            </span>
          </div>

          {/* Photo Actions */}
          <div className="flex-1 space-y-3 text-center sm:text-left">
            <div>
              <h3 className="text-sm font-bold text-white">{user?.full_name}</h3>
              <p className="text-xs text-slate-400 capitalize">
                {user?.role === 'admin' ? 'Administrator' : user?.role || 'Inspector'} ·{' '}
                {user?.organization || 'Legal Metrology Department'}
              </p>
              <p className="text-[11px] text-slate-500 mt-1">
                JPG, JPEG, PNG, or WEBP up to 3MB. Profile photo is optional.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 justify-center sm:justify-start pt-1">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/jpg,image/png,image/webp"
                className="hidden"
                onChange={handlePhotoSelect}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isPhotoBusy}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-800 border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition-all shadow-md"
              >
                <UploadCloud className="h-3.5 w-3.5 text-emerald-400" />
                {photoPreview || user?.profile_photo_url ? 'Change Photo' : 'Upload Photo'}
              </button>

              {photoPreview && (
                <button
                  type="button"
                  onClick={handleSavePhoto}
                  disabled={isPhotoBusy}
                  className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 px-4 py-2 text-xs font-bold text-white hover:from-emerald-500 hover:to-teal-400 transition-all shadow-md"
                >
                  <Save className="h-3.5 w-3.5" />
                  {isPhotoBusy ? 'Saving...' : 'Save Photo'}
                </button>
              )}

              {(photoPreview || user?.profile_photo_url) && (
                <button
                  type="button"
                  onClick={() => {
                    if (photoPreview) {
                      setPhotoPreview(null);
                      setPhotoFile(null);
                    } else {
                      handleRemovePhoto();
                    }
                  }}
                  disabled={isPhotoBusy}
                  className="inline-flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3.5 py-2 text-xs font-semibold text-rose-300 hover:bg-rose-500/20 transition-all"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Remove
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Account Details & Password Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Form 1: Account Details */}
        <form onSubmit={handleSaveDetails} className="rounded-3xl border border-[#1e2a4a] bg-[#0c1328] p-6 space-y-4 shadow-xl">
          <h2 className="flex items-center gap-2 font-bold text-white text-sm">
            <UserRound className="h-4 w-4 text-emerald-400" />
            Account Details
          </h2>
          <label className="block text-xs font-semibold text-slate-300">
            Full Name
            <input
              className="auth-input mt-1"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              minLength={2}
            />
          </label>
          <label className="block text-xs font-semibold text-slate-300">
            Email Address
            <input className="auth-input mt-1 opacity-60 cursor-not-allowed" value={user?.email || ''} readOnly />
          </label>
          <label className="block text-xs font-semibold text-slate-300">
            Organization
            <input
              className="auth-input mt-1"
              value={organization}
              onChange={(e) => setOrganization(e.target.value)}
              placeholder="e.g. Department of Consumer Affairs"
            />
          </label>
          <p className="text-[11px] text-slate-500 pt-1">
            Role: <span className="capitalize text-slate-400 font-semibold">{user?.role}</span> &middot; Member since{' '}
            {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
          </p>
          <button
            type="submit"
            className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 px-5 py-2.5 text-xs font-bold text-white hover:from-emerald-500 hover:to-teal-400 shadow-md shadow-emerald-700/20 transition-all"
          >
            <Save className="h-3.5 w-3.5" />
            Save Profile Changes
          </button>
        </form>

        {/* Form 2: Change Password */}
        <form onSubmit={handleChangePassword} className="rounded-3xl border border-[#1e2a4a] bg-[#0c1328] p-6 space-y-4 shadow-xl">
          <h2 className="flex items-center gap-2 font-bold text-white text-sm">
            <KeyRound className="h-4 w-4 text-amber-400" />
            Security & Password
          </h2>
          <label className="block text-xs font-semibold text-slate-300">
            Current Password
            <input
              className="auth-input mt-1"
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
              placeholder="••••••••"
            />
          </label>
          <label className="block text-xs font-semibold text-slate-300">
            New Password
            <input
              className="auth-input mt-1"
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
              minLength={8}
              placeholder="••••••••"
            />
          </label>
          <label className="block text-xs font-semibold text-slate-300">
            Confirm New Password
            <input
              className="auth-input mt-1"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              placeholder="••••••••"
            />
          </label>
          <button
            type="submit"
            className="rounded-xl bg-slate-800 border border-slate-700 px-5 py-2.5 text-xs font-bold text-slate-200 hover:bg-slate-700 hover:text-white shadow-md transition-all"
          >
            Update Password
          </button>
        </form>
      </div>
    </div>
  );
};

