import { decodeHtml } from '../../utils/helpers';

export default function DataTable({ headers = [], rows = [] }) {
  if (!rows.length && !headers.length) return null;
  return (
    <div className="table-wrap">
      <table>
        {headers.length > 0 && (
          <thead>
            <tr>
              {headers.map((header, index) => (
                <th key={`${header}-${index}`}>{decodeHtml(header)}</th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} data-label={decodeHtml(headers[cellIndex] || '')}>
                  {decodeHtml(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
