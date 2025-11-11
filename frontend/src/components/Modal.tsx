import React from 'react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  type?: 'info' | 'error' | 'success' | 'warning';
  showConfirm?: boolean;
  confirmText?: string;
  cancelText?: string;
  onConfirm?: () => void;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  type = 'info',
  showConfirm = false,
  confirmText = 'OK',
  cancelText = 'Cancel',
  onConfirm,
}) => {
  if (!isOpen) return null;

  const handleConfirm = () => {
    if (onConfirm) {
      onConfirm();
    }
    onClose();
  };

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      if (!showConfirm) {
        onClose();
      }
    }
  };

  const getTypeColor = () => {
    switch (type) {
      case 'error':
        return '#d32f2f';
      case 'success':
        return '#4caf50';
      case 'warning':
        return '#ff9800';
      default:
        return '#ffd700';
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0, 0, 0, 0.75)' }}
      onClick={handleBackdropClick}
    >
      <div
        className="osrs-card relative max-w-md w-full mx-4"
        style={{
          border: `3px solid ${getTypeColor()}`,
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.8)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="px-6 py-4 border-b"
          style={{
            borderColor: '#8b7355',
            backgroundColor: '#1a1510',
          }}
        >
          <h2
            className="osrs-card-title text-xl m-0"
            style={{ color: getTypeColor() }}
          >
            {title}
          </h2>
        </div>

        {/* Body */}
        <div className="px-6 py-4 osrs-text">
          {children}
        </div>

        {/* Footer */}
        <div
          className="px-6 py-4 border-t flex justify-end gap-3"
          style={{ borderColor: '#8b7355' }}
        >
          {showConfirm ? (
            <>
              <button
                onClick={onClose}
                className="osrs-btn"
                style={{
                  backgroundColor: '#3a3024',
                  color: '#8b7355',
                  borderColor: '#8b7355',
                }}
              >
                {cancelText}
              </button>
              <button
                onClick={handleConfirm}
                className="osrs-btn"
                style={{
                  backgroundColor: '#3a3024',
                  color: getTypeColor(),
                  borderColor: getTypeColor(),
                }}
              >
                {confirmText}
              </button>
            </>
          ) : (
            <button
              onClick={onClose}
              className="osrs-btn"
              style={{
                backgroundColor: '#3a3024',
                color: getTypeColor(),
                borderColor: getTypeColor(),
              }}
            >
              {confirmText}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

