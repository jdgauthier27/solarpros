import type { CSSProperties } from "react";
import type { BOMLineItem } from "../../api/client";
import type { CellAddress, EditableField } from "./useGridNavigation";
import GridCell from "./GridCell";

interface Props {
  item: BOMLineItem;
  index: number;
  selectedCell: CellAddress | null;
  isEditing: boolean;
  editValue: string;
  saveStatus: Map<string, "saving" | "saved">;
  onSelectCell: (cell: CellAddress | null) => void;
  onStartEditing: (initialValue?: string) => void;
  onEditValueChange: (value: string) => void;
  onDelete: (itemId: string) => void;
}

const cellStyle: CSSProperties = {
  padding: "6px 8px",
  borderBottom: "1px solid #eee",
  fontSize: 13,
};

const fmt = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });

export default function BOMLineItemRow({
  item,
  index,
  selectedCell,
  isEditing,
  editValue,
  saveStatus,
  onSelectCell,
  onStartEditing,
  onEditValueChange,
  onDelete,
}: Props) {
  const lineTotal = item.quantity * item.unit_cost;

  const isCellSelected = (field: EditableField) =>
    selectedCell?.itemId === item.id && selectedCell?.field === field;

  const isCellEditing = (field: EditableField) =>
    isCellSelected(field) && isEditing;

  const getCellSaveStatus = (field: EditableField) =>
    saveStatus.get(`${item.id}:${field}`);

  const aiBadge =
    item.ai_extracted && !item.user_modified ? (
      <span
        style={{
          background: "#e3f2fd",
          color: "#1565c0",
          padding: "1px 5px",
          borderRadius: 3,
          fontSize: 10,
          fontWeight: 600,
          flexShrink: 0,
        }}
        title="AI extracted"
      >
        AI
      </span>
    ) : undefined;

  const description = item.description ? (
    <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>
      {item.description}
    </div>
  ) : undefined;

  return (
    <tr style={{ background: index % 2 === 0 ? "#fff" : "#fafafa" }}>
      {/* Row number */}
      <td style={{ ...cellStyle, textAlign: "center", color: "#999", width: 36 }}>
        {index + 1}
      </td>

      {/* Name (editable) */}
      <GridCell
        itemId={item.id}
        field="name"
        value={item.name}
        isSelected={isCellSelected("name")}
        isEditing={isCellEditing("name")}
        editValue={isCellSelected("name") ? editValue : ""}
        saveStatus={getCellSaveStatus("name")}
        onSelect={onSelectCell}
        onStartEditing={() => onStartEditing()}
        onEditValueChange={onEditValueChange}
        badge={aiBadge}
        subtitle={description}
      />

      {/* Specifications (read-only) */}
      <td style={{ ...cellStyle, fontSize: 11, color: "#666" }}>
        {item.specifications
          ? Object.values(item.specifications).slice(0, 3).join(", ")
          : ""}
      </td>

      {/* Quantity (editable) */}
      <GridCell
        itemId={item.id}
        field="quantity"
        value={item.quantity}
        isSelected={isCellSelected("quantity")}
        isEditing={isCellEditing("quantity")}
        editValue={isCellSelected("quantity") ? editValue : ""}
        saveStatus={getCellSaveStatus("quantity")}
        onSelect={onSelectCell}
        onStartEditing={() => onStartEditing()}
        onEditValueChange={onEditValueChange}
        align="center"
      />

      {/* Unit (editable) */}
      <GridCell
        itemId={item.id}
        field="unit"
        value={item.unit}
        isSelected={isCellSelected("unit")}
        isEditing={isCellEditing("unit")}
        editValue={isCellSelected("unit") ? editValue : ""}
        saveStatus={getCellSaveStatus("unit")}
        onSelect={onSelectCell}
        onStartEditing={() => onStartEditing()}
        onEditValueChange={onEditValueChange}
        align="center"
      />

      {/* Unit Cost (editable) */}
      <GridCell
        itemId={item.id}
        field="unit_cost"
        value={item.unit_cost}
        displayValue={isCellEditing("unit_cost") ? undefined : fmt(item.unit_cost)}
        isSelected={isCellSelected("unit_cost")}
        isEditing={isCellEditing("unit_cost")}
        editValue={isCellSelected("unit_cost") ? editValue : ""}
        saveStatus={getCellSaveStatus("unit_cost")}
        onSelect={onSelectCell}
        onStartEditing={() => onStartEditing()}
        onEditValueChange={onEditValueChange}
        align="right"
      />

      {/* Line Total (read-only) */}
      <td style={{ ...cellStyle, textAlign: "right", fontWeight: 500 }}>
        {fmt(lineTotal)}
      </td>

      {/* Delete button */}
      <td style={{ ...cellStyle, textAlign: "center", width: 36 }}>
        <button
          onClick={() => onDelete(item.id)}
          style={{
            background: "none",
            border: "none",
            color: "#f44336",
            cursor: "pointer",
            fontSize: 16,
            padding: "2px 4px",
          }}
          title="Delete item"
        >
          &times;
        </button>
      </td>
    </tr>
  );
}
