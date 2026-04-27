function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents || "{}");
    const tabName = payload.tab_name;
    const headers = Array.isArray(payload.headers) ? payload.headers : [];
    const rows = Array.isArray(payload.rows) ? payload.rows : [];

    if (!tabName || headers.length === 0) {
      return jsonResponse({ ok: false, error: "Missing tab_name or headers" }, 400);
    }

    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = spreadsheet.getSheetByName(tabName) || spreadsheet.insertSheet(tabName);
    const values = [headers].concat(rows);

    sheet.clearContents();
    sheet.getRange(1, 1, values.length, headers.length).setValues(values);

    return jsonResponse({
      ok: true,
      spreadsheetId: spreadsheet.getId(),
      tabName: tabName,
      rowCount: rows.length,
    });
  } catch (error) {
    return jsonResponse({ ok: false, error: String(error) }, 500);
  }
}

function jsonResponse(payload) {
  return ContentService
    .createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}
