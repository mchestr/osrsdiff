import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

interface SearchBarProps {
  onSearch?: () => void;
  className?: string;
}

export const SearchBar = ({ onSearch, className = '' }: SearchBarProps) => {
  const [searchTerm, setSearchTerm] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      navigate(`/players/${encodeURIComponent(searchTerm.trim())}`);
      setSearchTerm('');
      onSearch?.();
    }
  };

  return (
    <form onSubmit={handleSubmit} className={className}>
      <div className="relative">
        <input
          type="text"
          placeholder="Search player..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full lg:w-48 px-4 py-2 pl-10 text-sm border border-secondary-300 dark:border-secondary-600 rounded-lg bg-white dark:bg-secondary-800 text-secondary-900 dark:text-secondary-100 placeholder-secondary-400 dark:placeholder-secondary-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors"
        />
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <svg
            className="h-5 w-5 text-secondary-400 dark:text-secondary-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
      </div>
    </form>
  );
};

