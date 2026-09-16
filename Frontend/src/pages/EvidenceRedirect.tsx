import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '@/store/appStore';

// The Evidence Drawer is a global slide-over (rendered once in App.tsx), not a
// dedicated route — this exists only so the sidebar's "Confidence & Evidence"
// link lands somewhere real (Regional Overview, drawer open) instead of a
// blank Outlet.
export const EvidenceRedirect = () => {
  const navigate = useNavigate();
  const setEvidenceDrawerOpen = useAppStore((s) => s.setEvidenceDrawerOpen);

  useEffect(() => {
    setEvidenceDrawerOpen(true);
    navigate('/', { replace: true });
  }, [navigate, setEvidenceDrawerOpen]);

  return null;
};
