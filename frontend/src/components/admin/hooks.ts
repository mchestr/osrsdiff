import { useEffect, useState } from 'react';

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

export function useUrlSync(
  searchParams: URLSearchParams,
  setSearchParams: (params: URLSearchParams, options?: { replace?: boolean }) => void,
  activeSearch: string | null,
  limit: number,
  defaultLimit: number
): void {
  // Sync state to URL when search or limit changes
  useEffect(() => {
    const currentSearch = searchParams.get('search') || '';
    const currentLimit = searchParams.get('limit');
    const newSearch = activeSearch || '';
    const newLimit = limit !== defaultLimit ? limit.toString() : '';

    // Only update if params actually changed
    if (currentSearch !== newSearch || currentLimit !== newLimit) {
      const params = new URLSearchParams();

      if (activeSearch) {
        params.set('search', activeSearch);
      }
      if (limit !== defaultLimit) {
        params.set('limit', limit.toString());
      }

      setSearchParams(params, { replace: true });
    }
  }, [activeSearch, limit, searchParams, setSearchParams, defaultLimit]);
}

