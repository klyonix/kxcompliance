// The Table layout's column sizes, and the fields that hold a person.

// Fields whose value is a user, shown by name.
export const PERSON_FIELDS = [
	"responsible",
	"reviewer",
	"owner",
	"modified_by",
	"closed_by",
	"checked_by",
];

const REM_PER_PX = 1 / 16;
const FIRST_MIN_REM = 14;
const OTHER_MIN_REM = 9;

// A grid track for a column: its chosen width, else a share of the room left; the first column,
// the record's name, takes twice the share.
export function columnTrack(column, index) {
	if (column.width) return `${Math.round(Number(column.width))}px`;
	return index === 0 ? `minmax(${FIRST_MIN_REM}rem, 2fr)` : `minmax(${OTHER_MIN_REM}rem, 1fr)`;
}

// The narrowest the table may be before it scrolls sideways, in rem.
export function tableMinWidth(columns) {
	return columns.reduce((total, column, index) => {
		if (column.width) return total + Number(column.width) * REM_PER_PX;
		return total + (index === 0 ? FIRST_MIN_REM : OTHER_MIN_REM);
	}, 0);
}
