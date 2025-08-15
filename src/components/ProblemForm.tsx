import React, { useRef, useState, useEffect } from 'react';
import { useHistoryData } from '../providers/HistoryProvider';
import { useAuth } from '../providers/AuthProvider';
import { storage, firebaseConfigured } from '../lib/firebase';
import { getDownloadURL, ref, uploadBytes } from 'firebase/storage';
import { FiImage, FiCheck, FiAlertCircle, FiLoader, FiSend } from 'react-icons/fi';

type FormState = {
  problemText: string;
  imageUrl?: string;
};

type SubmissionStatus = 'idle' | 'uploading' | 'submitting' | 'success' | 'error';

export const ProblemForm: React.FC = () => {
  const { addItem, loading: historyLoading } = useHistoryData();
  const { user } = useAuth();
  const [form, setForm] = useState<FormState>({ problemText: '' });
  const [submissionStatus, setSubmissionStatus] = useState<SubmissionStatus>('idle');
  const [statusMessage, setStatusMessage] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Handle dynamic height
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setForm((f) => ({ ...f, problemText: value }));

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      const maxHeight = 5 * 28; // ~5 rows
      textareaRef.current.style.height =
        scrollHeight > maxHeight ? maxHeight + 'px' : scrollHeight + 'px';
    }
  };

  const uploadImage = async (file: File): Promise<string | undefined> => {
    if (!firebaseConfigured) {
      throw new Error('Firebase Storage not configured');
    }
    const fileRef = ref(storage, `problems/${Date.now()}-${file.name}`);
    await uploadBytes(fileRef, file);
    return await getDownloadURL(fileRef);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!user) {
      setStatusMessage('Please login to submit problems');
      setSubmissionStatus('error');
      return;
    }
    if (!form.problemText.trim()) {
      setStatusMessage('Problem description is required');
      setSubmissionStatus('error');
      return;
    }

    setSubmissionStatus('uploading');
    setStatusMessage('Uploading image...');

    try {
      let imageUrl: string | undefined = form.imageUrl;
      const file = fileInputRef.current?.files?.[0];

      if (file) {
        imageUrl = await uploadImage(file);
        setStatusMessage('Image uploaded! Submitting problem...');
      }

      setSubmissionStatus('submitting');
      setStatusMessage('Submitting to backend...');

      await addItem({
        title: form.problemText.trim().substring(0, 50) + '...',
        problemText: form.problemText.trim(),
        constraints: undefined,
        testCases: undefined,
        imageUrl,
      });

      setSubmissionStatus('success');
      setStatusMessage('Problem submitted successfully! Check history for solution.');

      setForm({ problemText: '', imageUrl: undefined });
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (textareaRef.current) textareaRef.current.style.height = 'auto';

      setTimeout(() => {
        setSubmissionStatus('idle');
        setStatusMessage('');
      }, 3000);

    } catch (error) {
      setSubmissionStatus('error');
      setStatusMessage(error instanceof Error ? error.message : 'Submission failed');

      setTimeout(() => {
        setSubmissionStatus('idle');
        setStatusMessage('');
      }, 5000);
    }
  };

  const getStatusIcon = () => {
    switch (submissionStatus) {
      case 'uploading':
      case 'submitting':
        return <FiLoader className="animate-spin" />;
      case 'success':
        return <FiCheck className="text-green-500" />;
      case 'error':
        return <FiAlertCircle className="text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    switch (submissionStatus) {
      case 'success':
        return 'text-green-500 bg-green-900/20 border-green-700';
      case 'error':
        return 'text-red-500 bg-red-900/20 border-red-700';
      case 'uploading':
      case 'submitting':
        return 'text-blue-400 bg-blue-900/20 border-blue-700';
      default:
        return '';
    }
  };

  return (
    <div className="h-screen flex flex-col bg-neutral-900 text-white">
      {/* Greeting when empty */}
      <div className="flex-1 flex items-center justify-center text-2xl font-semibold text-neutral-400">
        {form.problemText.trim() === '' && !form.imageUrl && `Hello ${user?.displayName || 'User'}`}
      </div>

      {/* Status Message */}
      {statusMessage && (
        <div className={`p-3 mx-4 mb-3 rounded-xl border shadow-sm flex items-center gap-2 ${getStatusColor()}`}>
          {getStatusIcon()}
          <span className="font-medium">{statusMessage}</span>
        </div>
      )}

      {/* Input Bar */}
      <form
        onSubmit={onSubmit}
        className="sticky bottom-10 left-0 right-0 bg-neutral-900 border-t border-neutral-800 px-4 py-3"
      >
        <div className="relative flex items-end bg-neutral-800 rounded-2xl shadow-md px-3 py-2 focus-within:ring-2 focus-within:ring-blue-500 transition-all w-full">
          {/* Image Preview inside input */}
          {form.imageUrl && (
            <div className="absolute top-2 left-2 w-12 h-12 rounded-lg overflow-hidden border border-neutral-700">
              <img
                src={form.imageUrl}
                alt="Preview"
                className="w-full h-full object-cover"
              />
            </div>
          )}

          {/* Image Upload */}
          <label className="cursor-pointer p-2 rounded-full hover:bg-neutral-700 transition-colors">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.[0]) {
                  setForm(f => ({ ...f, imageUrl: URL.createObjectURL(e.target.files![0]) }));
                }
              }}
            />
            <FiImage className="w-5 h-5 text-blue-400" />
          </label>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            name="problemText"
            value={form.problemText}
            onChange={handleChange}
            rows={1}
            placeholder="Describe your DSA problem..."
            required
            className={`flex-1 bg-transparent resize-none border-none focus:outline-none text-lg px-3 py-2 placeholder-neutral-500 text-white ${
              form.imageUrl ? 'pl-16' : ''
            }`}
          />

          {/* Send Button */}
          <button
            type="submit"
            disabled={submissionStatus !== 'idle' || historyLoading}
            className="p-2 rounded-full bg-blue-600 hover:bg-blue-700 disabled:opacity-60 transition-colors"
          >
            <FiSend className="w-5 h-5 text-white" />
          </button>
        </div>
      </form>
    </div>
  );
};
