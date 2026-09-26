本次旅行的生成器，扩展自 family-trip-web：餐厅 kind=restaurant；未知坐标 p=null，不绘制标记或相邻线段；保留文字、地址和名称导航。请用此版本生成当前旅行，避免旧生成器拒绝未知坐标。

运行：python3 web-renderer/scripts/generate.py tripData.json index.html

酒店坐标未核实时也允许 kind=hotel、p=null，地图跳过该点及相邻线段，城市行程保留名称、地址与导航入口。
