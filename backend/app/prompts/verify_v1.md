检查「回答」里的每一个具体说法（数字、名称、步骤、结论）是否都能在「资料」里找到依据。

## 资料

{{contexts}}

## 回答

{{answer}}

## 输出

只输出 JSON：`{"faithful": true, "unsupported": ["资料里找不到依据的说法"]}`。全部有依据时 `faithful` 为 true、`unsupported` 为空数组。「文档里没有提到」这类说明本身不算问题。
