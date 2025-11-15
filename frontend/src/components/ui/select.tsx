import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps {
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
  disabled?: boolean;
  label?: string;
  error?: string;
  helperText?: string;
  placeholder?: string;
  className?: string;
}

export const Select: React.FC<SelectProps> = ({
  value,
  options,
  onChange,
  disabled = false,
  label,
  error,
  helperText,
  placeholder = 'Select an option',
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState<{ top: number; left: number; width: number } | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const selectedOption = options.find((opt) => opt.value === value);

  useEffect(() => {
    const updatePosition = () => {
      if (buttonRef.current && isOpen) {
        const rect = buttonRef.current.getBoundingClientRect();
        const scrollY = window.scrollY;
        const scrollX = window.scrollX;

        const spaceBelow = window.innerHeight - rect.bottom;
        const spaceAbove = rect.top;
        const dropdownHeight = Math.min(options.length * 40 + 16, 200);

        const shouldPositionAbove = spaceBelow < dropdownHeight && spaceAbove > spaceBelow;

        setPosition({
          top: shouldPositionAbove
            ? rect.top + scrollY - dropdownHeight
            : rect.bottom + scrollY + 4,
          left: rect.left + scrollX,
          width: rect.width,
        });
      }
    };

    if (isOpen) {
      updatePosition();
      window.addEventListener('scroll', updatePosition, true);
      window.addEventListener('resize', updatePosition);
    }

    return () => {
      window.removeEventListener('scroll', updatePosition, true);
      window.removeEventListener('resize', updatePosition);
    };
  }, [isOpen, options.length]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleSelect = (optionValue: string) => {
    onChange(optionValue);
    setIsOpen(false);
  };

  const buttonClasses = `
    inline-flex items-center justify-between w-full px-4 py-2.5 text-sm font-medium
    text-secondary-900 dark:text-secondary-100
    bg-white dark:bg-secondary-800
    border border-secondary-300 dark:border-secondary-600
    rounded-lg
    hover:bg-gray-50 dark:hover:bg-secondary-700
    focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500
    transition-all duration-200
    ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
    ${className}
  `.trim().replace(/\s+/g, ' ');

  const dropdownContent = isOpen && position ? (
    <div
      ref={dropdownRef}
      className="fixed z-[60] bg-white dark:bg-secondary-800 border border-secondary-300 dark:border-secondary-600 rounded-md shadow-lg"
      style={{
        top: `${position.top}px`,
        left: `${position.left}px`,
        width: `${position.width}px`,
      }}
    >
      <ul className="p-2 text-sm text-secondary-900 dark:text-secondary-100 font-medium max-h-48 overflow-y-auto">
        {options.map((option) => (
          <li key={option.value}>
            <button
              type="button"
              onClick={() => handleSelect(option.value)}
              className={`inline-flex items-center w-full px-2 py-2 rounded hover:bg-gray-100 dark:hover:bg-secondary-700 hover:text-secondary-900 dark:hover:text-secondary-100 transition-colors ${
                value === option.value
                  ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                  : ''
              }`}
            >
              {option.label || option.value}
            </button>
          </li>
        ))}
      </ul>
    </div>
  ) : null;

  return (
    <div className="w-full">
      {label && (
        <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
        </label>
      )}
      <div className="relative">
        <button
          ref={buttonRef}
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          className={buttonClasses}
        >
          <span className="flex-1 text-left">
            {selectedOption ? selectedOption.label || selectedOption.value : placeholder}
          </span>
          <svg
            className={`w-4 h-4 ms-1.5 -me-0.5 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            aria-hidden="true"
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            fill="none"
            viewBox="0 0 24 24"
          >
            <path
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="m19 9-7 7-7-7"
            />
          </svg>
        </button>
      </div>
      {error && (
        <p className="mt-1.5 text-sm text-danger-500 dark:text-danger-400">{error}</p>
      )}
      {helperText && !error && (
        <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400">{helperText}</p>
      )}
      {createPortal(dropdownContent, document.body)}
    </div>
  );
};

