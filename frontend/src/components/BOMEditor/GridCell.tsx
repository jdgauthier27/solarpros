import React, { useEffect, useRef, type CSSProperties, type ReactNode } from "react";
import type { CellAddress, EditableField } from "./useGridNavigation";

interface Props {
  itemId: string;
  field: EditableField;
  value: string | number;
  displayValue?: string;
  isSelected: boolean;
  isEditing: boolean;
  editValue: string;
  saveStatus: "saving" | "saved" | undefined;
  onSelect: (cell: CellAddress) => void;
  onStartEditing: () => void;
  onEditValueChange: (value: string) => void;
  align?: "left" | "center" | "right";
  /** Rendered inline next to value when not editing (e.g. AI badge) */
  badge?: ReactNode;
  /** Rendered below value when not editing (e.g. description) */
  subtitle?: ReactNode;
}

const baseCellStyle: CSSProperties = {
  padding: "6px 8px",
  borderBottom: "1px solid #eee",
  fontSize: 13,
  position: "relative",
  cursor: "pointer",
  transition: "background 0.1s",
};

const inputStyle: CSSProperties = {
  width: "100%",
  padding: "2px 4px",
  border: "none",
  outline: "none",
  fontSize: 13,
  background: "transparent",
  boxSizing: "border-box",
};

const saveIndicatorStyle: CSSProperties = {
  position: "absolute",
  top: 2,
  right: 2,
  fontSize: 10,
  lineHeight: 1,
  pointerEvents: "none",
};

const GridCell = React.memo(function GridCell({
  itemId,
  field,
  value,
  displayValue,
  isSelected,
  isEditing,
  editValue,
  saveStatus,
  onSelect,
  onStartEditing,
  onEditValueChange,
  align = "left",
  badge,
  subtitle,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const cellRef = useRef<HTMLTableCellElement>(null);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  useEffect(() => {
    if (isSelected && !isEditing && cellRef.current) {
      cellRef.current.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
  }, [isSelected, isEditing]);

  const cellStyle: CSSProperties = {
    ...baseCellStyle,
    textAlign: align,
    outline: isSelected ? "2px solid #1a73e8" : "none",
    outlineOffset: -2,
    background: isSelected ? (isEditing ? "#fff" : "#e8f0fe") : undefined,
  };

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!isSelected) {
      onSelect({ itemId, field });
    } else if (!isEditing) {
      onStartEditing();
    }
  };

  const valueContent = isEditing ? (
    <input
      ref={inputRef}
      value={editValue}
      onChange={(e) => onEditValueChange(e.target.value)}
      style={{ ...inputStyle, textAlign: align }}
    />
  ) : (
    <span>{displayValue ?? String(value)}</span>
  );

  return (
    <td
      ref={cellRef}
      style={cellStyle}
      onClick={handleClick}
      role="gridcell"
      aria-selected={isSelected}
      tabIndex={isSelected ? 0 : -1}
    >
      {badge && !isEditing ? (
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {valueContent}
          {badge}
        </div>
      ) : (
        valueContent
      )}
      {!isEditing && subtitle}
      {saveStatus && (
        <span
          style={{
            ...saveIndicatorStyle,
            color: saveStatus === "saving" ? "#f57c00" : "#4caf50",
          }}
        >
          {saveStatus === "saving" ? "\u25CF" : "\u2713"}
        </span>
      )}
    </td>
  );
});

export default GridCell;
