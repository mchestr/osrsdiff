interface TaskExecutionPaginationProps {
  currentPage: number;
  totalPages: number;
  hasPreviousPage: boolean;
  hasNextPage: boolean;
  onPageChange: (newOffset: number) => void;
  offset: number;
  limit: number;
}

export const TaskExecutionPagination: React.FC<TaskExecutionPaginationProps> = ({
  currentPage,
  totalPages,
  hasPreviousPage,
  hasNextPage,
  onPageChange,
  offset,
  limit,
}) => {
  if (totalPages <= 1) {
    return null;
  }

  return (
    <div className="osrs-card">
      <div className="flex justify-end items-center">
        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(Math.max(0, offset - limit))}
            disabled={!hasPreviousPage}
            className="osrs-btn"
            style={{ opacity: hasPreviousPage ? 1 : 0.5 }}
          >
            Previous
          </button>
          <span className="osrs-text-secondary">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => onPageChange(offset + limit)}
            disabled={!hasNextPage}
            className="osrs-btn"
            style={{ opacity: hasNextPage ? 1 : 0.5 }}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
};

