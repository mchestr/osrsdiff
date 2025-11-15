import { useCallback, useState } from 'react';

export type ModalType = 'info' | 'error' | 'success' | 'warning';

export interface ModalState {
  isOpen: boolean;
  title: string;
  message: string | React.ReactNode;
  type: ModalType;
  showConfirm: boolean;
  confirmCallback: (() => void) | null;
}

export interface UseModalReturn {
  modalState: ModalState;
  showModal: (title: string, message: string | React.ReactNode, type?: ModalType) => void;
  showConfirmModal: (
    title: string,
    message: string | React.ReactNode,
    onConfirm: () => void,
    type?: ModalType
  ) => void;
  closeModal: () => void;
  handleConfirm: () => void;
}

/**
 * Custom hook for managing modal state consistently across components
 */
export const useModal = (): UseModalReturn => {
  const [modalState, setModalState] = useState<ModalState>({
    isOpen: false,
    title: '',
    message: '',
    type: 'info',
    showConfirm: false,
    confirmCallback: null,
  });

  const showModal = useCallback(
    (title: string, message: string | React.ReactNode, type: ModalType = 'info') => {
      setModalState({
        isOpen: true,
        title,
        message,
        type,
        showConfirm: false,
        confirmCallback: null,
      });
    },
    []
  );

  const showConfirmModal = useCallback(
    (
      title: string,
      message: string | React.ReactNode,
      onConfirm: () => void,
      type: ModalType = 'warning'
    ) => {
      setModalState({
        isOpen: true,
        title,
        message,
        type,
        showConfirm: true,
        confirmCallback: onConfirm,
      });
    },
    []
  );

  const closeModal = useCallback(() => {
    setModalState((prev) => ({
      ...prev,
      isOpen: false,
      confirmCallback: null,
    }));
  }, []);

  const handleConfirm = useCallback(() => {
    setModalState((prev) => {
      if (prev.confirmCallback) {
        prev.confirmCallback();
      }
      return {
        ...prev,
        isOpen: false,
        confirmCallback: null,
      };
    });
  }, []);

  return {
    modalState,
    showModal,
    showConfirmModal,
    closeModal,
    handleConfirm,
  };
};

