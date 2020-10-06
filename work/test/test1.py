import gviz_api

description = {"name": ("string", "Name"),
               "salary": ("number", "Salary"),
               "full_time": ("boolean", "Full Time Employee")}
data = [{"name": "Mike", "salary": (10000, "$10,000"), "full_time": True},
        {"name": "Jim", "salary": (800, "$800"), "full_time": False},
        {"name": "Alice", "salary": (12500, "$12,500"), "full_time": True},
        {"name": "Bob", "salary": (7000, "$7,000"), "full_time": True}]

data_table = gviz_api.DataTable(description)
data_table.LoadData(data)
print("Content-type: text/plain")
print()
print(data_table.ToJSonResponse(columns_order=("name", "salary", "full_time"),
                                order_by="salary"))
