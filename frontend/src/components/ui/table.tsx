import React from 'react';

interface TableProps {
  children: React.ReactNode;
  className?: string;
}

export const Table: React.FC<TableProps> = ({ children, className = '' }) => {
  return <table className={`w-full ${className}`}>{children}</table>;
};

interface TableHeaderProps {
  children: React.ReactNode;
  className?: string;
}

export const TableHeader: React.FC<TableHeaderProps> = ({ children, className = '' }) => {
  return <thead className={className}>{children}</thead>;
};

interface TableBodyProps {
  children: React.ReactNode;
  className?: string;
}

export const TableBody: React.FC<TableBodyProps> = ({ children, className = '' }) => {
  return <tbody className={className}>{children}</tbody>;
};

interface TableRowProps {
  children: React.ReactNode;
  className?: string;
  onClick?: (e: React.MouseEvent<HTMLTableRowElement>) => void;
}

export const TableRow: React.FC<TableRowProps> = ({ children, className = '', onClick }) => {
  return (
    <tr className={className} onClick={onClick}>
      {children}
    </tr>
  );
};

interface TableCellProps {
  children: React.ReactNode;
  className?: string;
  isHeader?: boolean;
  colSpan?: number;
  onClick?: (e: React.MouseEvent<HTMLTableCellElement>) => void;
}

export const TableCell: React.FC<TableCellProps> = ({
  children,
  className = '',
  isHeader = false,
  colSpan,
  onClick,
}) => {
  // Default padding: px-5 py-3 for headers, px-5 py-4 for cells (can be overridden via className)
  const baseHeaderClasses = 'px-5 py-3 text-start font-medium text-gray-500 text-theme-xs dark:text-gray-400';
  const baseCellClasses = 'px-5 py-4 text-start text-gray-500 text-theme-sm dark:text-gray-400';

  if (isHeader) {
    return (
      <th className={`${baseHeaderClasses} ${className}`} colSpan={colSpan} onClick={onClick}>
        {children}
      </th>
    );
  }

  return (
    <td className={`${baseCellClasses} ${className}`} colSpan={colSpan} onClick={onClick}>
      {children}
    </td>
  );
};

