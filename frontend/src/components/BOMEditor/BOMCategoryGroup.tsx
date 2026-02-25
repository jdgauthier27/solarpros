import type { CSSProperties } from "react";
import type { BOMLineItem } from "../../api/client";
import type { CellAddress } from "./useGridNavigation";
import BOMLineItemRow from "./BOMLineItemRow";

interface Props {
  category: string;
  items: BOMLineItem[];
  collapsed: boolean;
  onToggleCollapse: (category: string) => void;
  selectedCell: CellAddress | null;
  isEditing: boolean;
  editValue: string;
  saveStatus: Map<string, "saving" | "saved">;
  onSelectCell: (cell: CellAddress | null) => void;
  onStartEditing: (initialValue?: string) => void;
  onEditValueChange: (value: string) => void;
  onDelete: (itemId: string) => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  panel: "Panels",
  inverter: "Inverters",
  racking: "Racking & Mounting",
  electrical: "Electrical",
  battery: "Battery Storage",
  labor: "Labor",
  permit: "Permits & Fees",
  other: "Other",
};

const fmt = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });

const headerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "8px 12px",
  background: "#e8eaf6",
  cursor: "pointer",
  userSelect: "none",
  borderBottom: "1px solid #c5cae9",
};

export default function BOMCategoryGroup({
  category,
  items,
  collapsed,
  onToggleCollapse,
  selectedCell,
  isEditing,
  editValue,
  saveStatus,
  onSelectCell,
  onStartEditing,
  onEditValueChange,
  onDelete,
}: Props) {
  const subtotal = items.reduce((sum, i) => sum + i.quantity * i.unit_cost, 0);

  return (
    <>
      <tr>
        <td colSpan={8} style={{ padding: 0 }}>
          <div style={headerStyle} onClick={() => onToggleCollapse(category)}>
            <span style={{ fontWeight: 700, color: "#1a237e", fontSize: 13 }}>
              {collapsed ? "\u25B6" : "\u25BC"}{" "}
              {CATEGORY_LABELS[category] || category.toUpperCase()} ({items.length} items)
            </span>
            <span style={{ fontWeight: 600, color: "#1a237e", fontSize: 13 }}>
              {fmt(subtotal)}
            </span>
          </div>
        </td>
      </tr>
      {!collapsed &&
        items.map((item, i) => (
          <BOMLineItemRow
            key={item.id}
            item={item}
            index={i}
            selectedCell={selectedCell}
            isEditing={isEditing}
            editValue={editValue}
            saveStatus={saveStatus}
            onSelectCell={onSelectCell}
            onStartEditing={onStartEditing}
            onEditValueChange={onEditValueChange}
            onDelete={onDelete}
          />
        ))}
    </>
  );
}
