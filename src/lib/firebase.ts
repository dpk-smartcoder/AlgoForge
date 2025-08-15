import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';
import { getStorage } from 'firebase/storage';

const cfg = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY || 'demo',
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN || 'demo.firebaseapp.com',
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID || 'demo',
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET || 'demo.appspot.com',
  messagingSenderId: process.env.REACT_APP_FIREBASE_SENDER_ID || '0',
  appId: process.env.REACT_APP_FIREBASE_APP_ID || '1:0:web:demo',
};

const missing = [
  'REACT_APP_FIREBASE_API_KEY',
  'REACT_APP_FIREBASE_AUTH_DOMAIN',
  'REACT_APP_FIREBASE_PROJECT_ID',
  'REACT_APP_FIREBASE_STORAGE_BUCKET',
  'REACT_APP_FIREBASE_SENDER_ID',
  'REACT_APP_FIREBASE_APP_ID',
].filter((k) => !process.env[k as keyof NodeJS.ProcessEnv]);

if (missing.length) {
  // Surface a friendly message but keep app running for development
  // Login and uploads will be disabled until env is provided
  console.warn('Firebase env vars missing:', missing.join(', '));
  console.warn('Current config:', cfg);
} else {
  console.log('Firebase configured successfully:', {
    projectId: cfg.projectId,
    authDomain: cfg.authDomain
  });
}

const app = initializeApp(cfg);

export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
export const storage = getStorage(app);
export const firebaseConfigured = missing.length === 0;


