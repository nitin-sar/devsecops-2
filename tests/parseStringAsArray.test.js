const parseStringAsArray = require("../src/utils/parseStringAsArray");

describe("parseStringAsArray", () => {
  test("should convert comma-separated string into an array", () => {
    const result = parseStringAsArray("javascript,nodejs,devops");

    expect(result).toEqual([
      "javascript",
      "nodejs",
      "devops"
    ]);
  });

  test("should remove extra spaces", () => {
    const result = parseStringAsArray("javascript, nodejs, devops");

    expect(result).toEqual([
      "javascript",
      "nodejs",
      "devops"
    ]);
  });
});
