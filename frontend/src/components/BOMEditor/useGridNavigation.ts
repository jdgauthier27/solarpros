import { useState, useCallback, useRef, useEffect } from "react";
import type { BOMLineItem, BOMLineItemUpdatePayload } from "../../api/client";

export type EditableField = "name" | "quantity" | "unit" | "unit_cost";

export const EDITABLE_FIELDS: EditableField[] = ["name", "quantity", "unit", "unit_cost"];

export interface CellAddress {
  itemId: string;
  field: EditableField;
}

interface UndoEntry {
  itemId: string;
  field: EditableField;
  previousValue: string | number;
}

const MAX_UNDO = 20;
const DEBOUNCE_MS = 300;
const SAVED_DISPLAY_MS = 1500;

interface UseGridNavigationOptions {
  flatVisibleItems: string[];
  itemsById: Map<string, BOMLineItem>;
  onSave: (itemId: string, payload: BOMLineItemUpdatePayload) => void;
  onDelete: (itemId: string) => void;
}

export function useGridNavigation({
  flatVisibleItems,
  itemsById,
  onSave,
  onDelete,
}: UseGridNavigationOptions) {
  const [selectedCell, setSelectedCell] = useState<CellAddress | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const [saveStatus, setSaveStatus] = useState<Map<string, "saving" | "saved">>(new Map());
  const [, setUndoStack] = useState<UndoEntry[]>([]);

  const debounceTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const savedTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  // Refs for latest values (used in callbacks to avoid stale closures)
  const selectedCellRef = useRef(selectedCell);
  selectedCellRef.current = selectedCell;
  const isEditingRef = useRef(isEditing);
  isEditingRef.current = isEditing;
  const editValueRef = useRef(editValue);
  editValueRef.current = editValue;

  // Cleanup debounce timers on unmount
  useEffect(() => {
    return () => {
      debounceTimers.current.forEach((t) => clearTimeout(t));
      savedTimers.current.forEach((t) => clearTimeout(t));
    };
  }, []);

  // Deselect if selected cell is no longer visible (e.g. category collapsed)
  useEffect(() => {
    if (selectedCell && !flatVisibleItems.includes(selectedCell.itemId)) {
      setSelectedCell(null);
      setIsEditing(false);
    }
  }, [selectedCell, flatVisibleItems]);

  const getFieldValue = useCallback(
    (itemId: string, field: EditableField): string | number => {
      const item = itemsById.get(itemId);
      if (!item) return "";
      return item[field];
    },
    [itemsById],
  );

  const setCellSaveStatus = useCallback(
    (key: string, status: "saving" | "saved" | null) => {
      setSaveStatus((prev) => {
        const next = new Map(prev);
        if (status === null) {
          next.delete(key);
        } else {
          next.set(key, status);
        }
        return next;
      });
    },
    [],
  );

  const debouncedSave = useCallback(
    (itemId: string, field: EditableField, value: string | number) => {
      const key = `${itemId}:${field}`;

      const existing = debounceTimers.current.get(key);
      if (existing) clearTimeout(existing);
      const existingSaved = savedTimers.current.get(key);
      if (existingSaved) clearTimeout(existingSaved);

      setCellSaveStatus(key, "saving");

      const timer = setTimeout(() => {
        debounceTimers.current.delete(key);

        const payload: BOMLineItemUpdatePayload = {};
        if (field === "name") payload.name = value as string;
        if (field === "quantity") payload.quantity = value as number;
        if (field === "unit") payload.unit = value as string;
        if (field === "unit_cost") payload.unit_cost = value as number;

        onSave(itemId, payload);

        setCellSaveStatus(key, "saved");
        const savedTimer = setTimeout(() => {
          setCellSaveStatus(key, null);
          savedTimers.current.delete(key);
        }, SAVED_DISPLAY_MS);
        savedTimers.current.set(key, savedTimer);
      }, DEBOUNCE_MS);

      debounceTimers.current.set(key, timer);
    },
    [onSave, setCellSaveStatus],
  );

  const getNextCell = useCallback(
    (current: CellAddress, direction: "next" | "prev"): CellAddress | null => {
      const fieldIdx = EDITABLE_FIELDS.indexOf(current.field);
      const rowIdx = flatVisibleItems.indexOf(current.itemId);
      if (fieldIdx === -1 || rowIdx === -1) return null;

      if (direction === "next") {
        if (fieldIdx < EDITABLE_FIELDS.length - 1) {
          return { itemId: current.itemId, field: EDITABLE_FIELDS[fieldIdx + 1] };
        }
        if (rowIdx < flatVisibleItems.length - 1) {
          return { itemId: flatVisibleItems[rowIdx + 1], field: EDITABLE_FIELDS[0] };
        }
        return null;
      } else {
        if (fieldIdx > 0) {
          return { itemId: current.itemId, field: EDITABLE_FIELDS[fieldIdx - 1] };
        }
        if (rowIdx > 0) {
          return {
            itemId: flatVisibleItems[rowIdx - 1],
            field: EDITABLE_FIELDS[EDITABLE_FIELDS.length - 1],
          };
        }
        return null;
      }
    },
    [flatVisibleItems],
  );

  const getVerticalCell = useCallback(
    (current: CellAddress, direction: "up" | "down"): CellAddress | null => {
      const rowIdx = flatVisibleItems.indexOf(current.itemId);
      if (rowIdx === -1) return null;

      const newRowIdx = direction === "down" ? rowIdx + 1 : rowIdx - 1;
      if (newRowIdx < 0 || newRowIdx >= flatVisibleItems.length) return null;

      return { itemId: flatVisibleItems[newRowIdx], field: current.field };
    },
    [flatVisibleItems],
  );

  const commitEdit = useCallback(() => {
    const cell = selectedCellRef.current;
    if (!cell || !isEditingRef.current) return;

    const originalValue = getFieldValue(cell.itemId, cell.field);
    let newValue: string | number = editValueRef.current;

    if (cell.field === "quantity" || cell.field === "unit_cost") {
      newValue = parseFloat(editValueRef.current) || 0;
    }

    setIsEditing(false);

    if (String(newValue) !== String(originalValue)) {
      setUndoStack((prev) => {
        const next = [
          ...prev,
          { itemId: cell.itemId, field: cell.field, previousValue: originalValue },
        ];
        if (next.length > MAX_UNDO) next.shift();
        return next;
      });
      debouncedSave(cell.itemId, cell.field, newValue);
    }
  }, [getFieldValue, debouncedSave]);

  const cancelEdit = useCallback(() => {
    setIsEditing(false);
    setEditValue("");
  }, []);

  const startEditing = useCallback(
    (initialValue?: string) => {
      const cell = selectedCellRef.current;
      if (!cell) return;
      const currentValue = getFieldValue(cell.itemId, cell.field);
      setEditValue(initialValue ?? String(currentValue));
      setIsEditing(true);
    },
    [getFieldValue],
  );

  const selectCell = useCallback(
    (cell: CellAddress | null) => {
      if (isEditingRef.current) {
        commitEdit();
      }
      setSelectedCell(cell);
      setIsEditing(false);
    },
    [commitEdit],
  );

  const undo = useCallback(() => {
    setUndoStack((prev) => {
      if (prev.length === 0) return prev;
      const entry = prev[prev.length - 1];
      debouncedSave(entry.itemId, entry.field, entry.previousValue);
      setSelectedCell({ itemId: entry.itemId, field: entry.field });
      setIsEditing(false);
      return prev.slice(0, -1);
    });
  }, [debouncedSave]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const cell = selectedCellRef.current;
      if (!cell) return;

      if (isEditingRef.current) {
        // Edit mode — only intercept navigation keys
        switch (e.key) {
          case "Tab": {
            e.preventDefault();
            commitEdit();
            const next = e.shiftKey ? getNextCell(cell, "prev") : getNextCell(cell, "next");
            if (next) setSelectedCell(next);
            break;
          }
          case "Enter": {
            e.preventDefault();
            commitEdit();
            const down = getVerticalCell(cell, "down");
            if (down) setSelectedCell(down);
            break;
          }
          case "Escape": {
            e.preventDefault();
            cancelEdit();
            break;
          }
          // All other keys pass through to the input
        }
        return;
      }

      // Navigation mode
      switch (e.key) {
        case "Tab": {
          e.preventDefault();
          const next = e.shiftKey ? getNextCell(cell, "prev") : getNextCell(cell, "next");
          if (next) setSelectedCell(next);
          break;
        }
        case "Enter": {
          e.preventDefault();
          const down = getVerticalCell(cell, "down");
          if (down) setSelectedCell(down);
          break;
        }
        case "ArrowUp": {
          e.preventDefault();
          const up = getVerticalCell(cell, "up");
          if (up) setSelectedCell(up);
          break;
        }
        case "ArrowDown": {
          e.preventDefault();
          const down = getVerticalCell(cell, "down");
          if (down) setSelectedCell(down);
          break;
        }
        case "ArrowLeft": {
          e.preventDefault();
          const prev = getNextCell(cell, "prev");
          if (prev) setSelectedCell(prev);
          break;
        }
        case "ArrowRight": {
          e.preventDefault();
          const next = getNextCell(cell, "next");
          if (next) setSelectedCell(next);
          break;
        }
        case "Escape": {
          e.preventDefault();
          setSelectedCell(null);
          break;
        }
        case "Delete":
        case "Backspace": {
          e.preventDefault();
          if (window.confirm("Delete this row?")) {
            onDelete(cell.itemId);
            setSelectedCell(null);
          }
          break;
        }
        case "F2": {
          e.preventDefault();
          startEditing();
          break;
        }
        default: {
          if ((e.ctrlKey || e.metaKey) && e.key === "z") {
            e.preventDefault();
            undo();
          } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
            e.preventDefault();
            startEditing(e.key);
          }
          break;
        }
      }
    },
    [commitEdit, cancelEdit, startEditing, getNextCell, getVerticalCell, onDelete, undo],
  );

  return {
    selectedCell,
    isEditing,
    editValue,
    saveStatus,
    selectCell,
    startEditing,
    commitEdit,
    cancelEdit,
    handleKeyDown,
    setEditValue,
  };
}
