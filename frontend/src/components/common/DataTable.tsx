import { useMemo, useState, ReactNode } from 'react';
import { Table, TableBody, TableCell, TableHeader, TableRow } from '../ui';

export type SortDirection = 'asc' | 'desc' | null;

export interface Column<T> {
  key: string;
  label: string;
  sortable?: boolean;
  render?: (item: T) => ReactNode;
  className?: string;
  headerClassName?: string;
  sortFn?: (a: T, b: T) => number;
}

export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  hasPreviousPage: boolean;
  hasNextPage: boolean;
  onPageChange: (newOffset: number) => void;
  offset: number;
  limit: number;
}

export interface SearchConfig<T extends Record<string, any>> {
  placeholder?: string;
  searchKeys?: (keyof T)[];
  value?: string;
  onChange?: (value: string) => void;
  onReset?: () => void;
  showClearButton?: boolean;
  isFiltering?: boolean;
}

export interface LimitConfig {
  value: number;
  onChange: (limit: number) => void;
  options?: number[];
}

export interface DataTableProps<T extends Record<string, any>> {
  data: T[];
  columns: Column<T>[];
  keyExtractor: (item: T) => string | number;
  emptyMessage?: string;
  searchable?: boolean | SearchConfig<T>;
  searchPlaceholder?: string; // Deprecated, use searchable object
  searchKeys?: (keyof T)[]; // Deprecated, use searchable object
  onRowClick?: (item: T, e?: React.MouseEvent) => void;
  className?: string;
  rowClassName?: string | ((item: T) => string);
  pagination?: PaginationProps;
  showResultsCount?: boolean;
  limitConfig?: LimitConfig;
}

export function DataTable<T extends Record<string, any>>({
  data,
  columns,
  keyExtractor,
  emptyMessage = 'No data available',
  searchable = false,
  searchPlaceholder = 'Search...',
  searchKeys,
  onRowClick,
  className = '',
  rowClassName = '',
  pagination,
  showResultsCount = true,
  limitConfig,
}: DataTableProps<T>) {
  // Handle searchable prop - can be boolean or SearchConfig object
  const isSearchable = typeof searchable === 'boolean' ? searchable : !!searchable;
  const searchConfig = typeof searchable === 'object' ? searchable : undefined;
  const isExternalSearch = !!searchConfig?.onChange;

  // Internal search state (for client-side search)
  const [internalSearchTerm, setInternalSearchTerm] = useState('');
  // External search uses searchConfig.value
  const searchTerm = isExternalSearch ? (searchConfig?.value || '') : internalSearchTerm;

  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  // Filter data based on search term (only for client-side search)
  const filteredData = useMemo(() => {
    if (isExternalSearch) {
      // External search - data is already filtered by server
      return data;
    }

    if (!isSearchable || !searchTerm.trim()) {
      return data;
    }

    const term = searchTerm.toLowerCase();
    const keysToSearch = searchConfig?.searchKeys || searchKeys;

    return data.filter((item) => {
      if (keysToSearch) {
        return keysToSearch.some((key) => {
          const value = item[key as keyof T];
          return value?.toString().toLowerCase().includes(term);
        });
      }
      // Default: search all string/number values
      return Object.values(item).some((value) =>
        value?.toString().toLowerCase().includes(term)
      );
    });
  }, [data, searchTerm, isSearchable, isExternalSearch, searchConfig?.searchKeys, searchKeys]);

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortColumn || !sortDirection) {
      return filteredData;
    }

    const column = columns.find((col) => col.key === sortColumn);
    if (!column || !column.sortable) {
      return filteredData;
    }

    const sorted = [...filteredData].sort((a, b) => {
      if (column.sortFn) {
        return column.sortFn(a, b);
      }
      // Default sorting
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return aVal - bVal;
      }

      return aVal.toString().localeCompare(bVal.toString());
    });

    return sortDirection === 'desc' ? sorted.reverse() : sorted;
  }, [filteredData, sortColumn, sortDirection, columns]);

  const handleSort = (columnKey: string) => {
    const column = columns.find((col) => col.key === columnKey);
    if (!column?.sortable) return;

    if (sortColumn === columnKey) {
      // Cycle through: asc -> desc -> null
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else if (sortDirection === 'desc') {
        setSortDirection(null);
        setSortColumn(null);
      }
    } else {
      setSortColumn(columnKey);
      setSortDirection('asc');
    }
  };

  const getSortIcon = (columnKey: string) => {
    if (sortColumn !== columnKey) {
      return (
        <svg
          className="w-4 h-4 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"
          />
        </svg>
      );
    }

    if (sortDirection === 'asc') {
      return (
        <svg
          className="w-4 h-4 text-primary-600 dark:text-primary-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 15l7-7 7 7"
          />
        </svg>
      );
    }

    if (sortDirection === 'desc') {
      return (
        <svg
          className="w-4 h-4 text-primary-600 dark:text-primary-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      );
    }

    return null;
  };

  const getRowClassName = (item: T): string => {
    const baseClass = '';
    const customClass = typeof rowClassName === 'function' ? rowClassName(item) : rowClassName;
    return `${baseClass} ${customClass}`.trim();
  };

  const handleRowClick = (item: T, e: React.MouseEvent<HTMLTableRowElement>) => {
    // Don't trigger row click if clicking on interactive elements
    const target = e.target as HTMLElement;
    if (
      target.closest('button') ||
      target.closest('a') ||
      target.closest('input') ||
      target.closest('select')
    ) {
      return;
    }
    onRowClick?.(item, e);
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (isExternalSearch && searchConfig?.onChange) {
      searchConfig.onChange(value);
    } else {
      setInternalSearchTerm(value);
    }
  };

  const handleSearchReset = () => {
    if (isExternalSearch && searchConfig?.onReset) {
      searchConfig.onReset();
    } else {
      setInternalSearchTerm('');
    }
  };

  const searchPlaceholderText = searchConfig?.placeholder || searchPlaceholder;
  // Show clear button if explicitly enabled in config, or if using simple boolean searchable and there's a term
  const showClearButton =
    (searchConfig?.showClearButton === true && searchTerm.length > 0) ||
    (!searchConfig && isSearchable && searchTerm.length > 0);

  return (
    <div className={`overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/[0.05] dark:bg-white/[0.03] ${className}`}>
      {/* Search Bar */}
      {isSearchable && (
        <div className="p-4 border-b border-gray-200 dark:border-white/[0.05]">
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
            <div className="flex-1 w-full sm:w-auto">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg
                    className="h-5 w-5 text-gray-400"
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
                <input
                  type="text"
                  value={searchTerm}
                  onChange={handleSearchChange}
                  placeholder={searchPlaceholderText}
                  className="input pl-10 w-full"
                />
                {searchConfig?.isFiltering && (
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-400"></div>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              {showClearButton && (
                <button
                  onClick={handleSearchReset}
                  className="osrs-btn whitespace-nowrap"
                >
                  Clear
                </button>
              )}

              {limitConfig && (
                <div className="flex items-center gap-2">
                  <label className="text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">Limit:</label>
                  <select
                    value={limitConfig.value}
                    onChange={(e) => limitConfig.onChange(parseInt(e.target.value, 10))}
                    className="input"
                  >
                    {(limitConfig.options || [25, 50, 100, 200]).map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="max-w-full overflow-x-auto">
        <Table>
          <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
            <TableRow>
              {columns.map((column) => (
                <TableCell
                  key={column.key}
                  isHeader
                  className={`
                    ${column.sortable ? 'cursor-pointer select-none hover:bg-gray-50 dark:hover:bg-white/[0.05]' : ''}
                    ${column.headerClassName || ''}
                  `}
                  onClick={() => column.sortable && handleSort(column.key)}
                >
                  <div className="flex items-center gap-2">
                    <span>{column.label}</span>
                    {column.sortable && getSortIcon(column.key)}
                  </div>
                </TableCell>
              ))}
            </TableRow>
          </TableHeader>

          <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
            {sortedData.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="py-8 text-center"
                >
                  {emptyMessage}
                </TableCell>
              </TableRow>
            ) : (
              sortedData.map((item) => (
                <TableRow
                  key={keyExtractor(item)}
                  className={getRowClassName(item)}
                  onClick={(e) => handleRowClick(item, e)}
                >
                  {columns.map((column) => (
                    <TableCell
                      key={column.key}
                      className={column.className || ''}
                    >
                      {column.render ? column.render(item) : item[column.key]}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Footer: Results Count and Pagination */}
      {(showResultsCount || pagination) && (
        <div className="p-4 border-t border-gray-200 dark:border-white/[0.05] flex flex-col sm:flex-row justify-between items-center gap-4">
          {/* Results Count */}
          {showResultsCount && sortedData.length > 0 && (
            <div className="text-theme-sm text-gray-500 dark:text-gray-400">
              Showing {sortedData.length} of {data.length} {data.length === 1 ? 'item' : 'items'}
              {searchTerm && ` (filtered from ${data.length} total)`}
            </div>
          )}

          {/* Pagination */}
          {pagination && pagination.totalPages > 1 && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => pagination.onPageChange(Math.max(0, pagination.offset - pagination.limit))}
                disabled={!pagination.hasPreviousPage}
                className="osrs-btn px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-theme-sm text-gray-700 dark:text-gray-300 px-2">
                Page {pagination.currentPage} of {pagination.totalPages}
              </span>
              <button
                onClick={() => pagination.onPageChange(pagination.offset + pagination.limit)}
                disabled={!pagination.hasNextPage}
                className="osrs-btn px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
