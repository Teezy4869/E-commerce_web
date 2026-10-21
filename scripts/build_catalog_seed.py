"""Build the checked-in SQLite seed while leaving the 12 search fixtures untouched.

Run only when intentionally updating dataset/catalog_seed.json. Live databases are
never overwritten by this script.
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "dataset" / "products.json"
OUTPUT = ROOT / "dataset" / "catalog_seed.json"

# id, slug, Vietnamese name, category, color, material, VND price, description
NEW = [
    (13, "ao-so-mi-cotton-trang-nga", "Áo sơ mi cotton trắng ngà", "shirt", "Trắng ngà", "100% cotton", 649000, "Sơ mi cotton đứng phom, cổ nhọn và túi ngực tinh giản."),
    (14, "ao-so-mi-linen-xanh-sage", "Áo sơ mi linen xanh sage", "shirt", "Xanh sage", "100% linen", 729000, "Chất linen thoáng nhẹ, sắc xanh dịu cho ngày nắng."),
    (15, "quan-tay-xam-than", "Quần tây xám than", "trousers", "Xám than", "Polyester pha viscose", 899000, "Quần tây ống suông với đường ly gọn gàng."),
    (16, "quan-ong-rong-kem", "Quần ống rộng màu kem", "trousers", "Kem", "Linen pha cotton", 849000, "Phom ống rộng thoải mái, bề mặt vải mềm và rủ."),
    (17, "ao-thun-oversize-essential", "Áo thun oversize Essential", "shirt", "Xanh rừng", "100% cotton", 399000, "Áo thun vai rơi bằng cotton dày vừa, có hai gam màu dễ phối."),
    (18, "ao-polo-det-den", "Áo polo dệt đen", "shirt", "Đen", "Cotton dệt kim", 579000, "Polo cổ bẻ dệt kim cho vẻ chỉn chu mà vẫn thoải mái."),
    (19, "ao-so-mi-oxford-xanh", "Áo sơ mi Oxford xanh nhạt", "shirt", "Xanh nhạt", "Cotton Oxford", 699000, "Sơ mi Oxford cổ cài nút, dễ mặc đi làm và cuối tuần."),
    (20, "ao-so-mi-linen-cat", "Áo sơ mi linen màu cát", "shirt", "Cát", "100% linen", 649000, "Sơ mi cổ mở ngắn tay, sắc cát ấm và thoáng mát."),
    (21, "quan-jeans-ong-dung-indigo", "Quần jeans ống đứng indigo", "trousers", "Indigo", "Denim cotton", 899000, "Denim indigo ống đứng, thiết kế cổ điển dễ phối."),
    (22, "quan-cargo-xanh-olive", "Quần cargo xanh olive", "trousers", "Xanh olive", "Cotton twill", 929000, "Quần cargo nhiều túi với độ bền cho nhịp sống năng động."),
    (23, "quan-chino-nau-socola", "Quần chino nâu socola", "trousers", "Nâu socola", "Cotton twill", 799000, "Chino ống thoải mái, sắc nâu trầm linh hoạt."),
    (24, "quan-xep-ly-den", "Quần xếp ly đen", "trousers", "Đen", "Polyester pha viscose", 949000, "Đường xếp ly sắc nét trên phom quần suông hiện đại."),
    (25, "quan-chino-be", "Quần chino màu be", "trousers", "Be", "Cotton twill", 779000, "Chino dáng côn vừa, tông be nhẹ cho nhiều dịp."),
    (26, "giay-sneaker-da-trang", "Giày sneaker da trắng", "shoes", "Trắng", "Da tổng hợp, đế cao su", 1290000, "Sneaker trắng tối giản với đế êm cho những ngày di chuyển."),
    (27, "giay-loafer-da-nau", "Giày loafer da nâu", "shoes", "Nâu", "Da bò, đế cao su", 1590000, "Loafer da nâu thanh lịch, đường may tinh gọn."),
    (28, "giay-boot-da-den", "Giày boot da đen", "shoes", "Đen", "Da bò, đế cao su", 1790000, "Boot cổ thấp da đen tạo điểm nhấn vững chãi."),
    (29, "giay-canvas-xanh-sage", "Giày canvas xanh sage", "shoes", "Xanh sage", "Canvas cotton, đế cao su", 890000, "Canvas thấp cổ xanh sage cho trang phục thường ngày."),
    (30, "giay-derby-da-lon-cat", "Giày derby da lộn màu cát", "shoes", "Cát", "Da lộn, đế cao su", 1690000, "Derby da lộn màu cát với phom gọn và mềm."),
    (31, "ao-thun-co-tron-xanh-rung", "Áo thun cổ tròn xanh rừng", "shirt", "Xanh rừng", "100% cotton", 369000, "Áo thun cotton mềm với cổ tròn gọn và sắc xanh rừng dễ phối."),
    (32, "ao-polo-pique-kem", "Áo polo piqué màu kem", "shirt", "Kem", "Cotton piqué", 619000, "Polo piqué thoáng nhẹ, cổ bẻ tối giản cho ngày thường."),
    (33, "ao-so-mi-ke-soc-xanh-trang", "Áo sơ mi kẻ sọc xanh trắng", "shirt", "Xanh trắng", "100% cotton", 759000, "Sơ mi tay dài sọc dọc thanh thoát, chất cotton thoáng."),
    (34, "ao-blouse-linen-tay-bong-kem", "Áo blouse linen tay bồng màu kem", "shirt", "Kem", "Linen pha cotton", 689000, "Blouse tay bồng nhẹ với dáng thoải mái và sắc kem dịu."),
    (35, "ao-henley-waffle-nau-cacao", "Áo henley waffle nâu cacao", "shirt", "Nâu cacao", "Cotton waffle", 659000, "Henley tay dài dệt waffle, cổ cài nút và bề mặt vải giàu kết cấu."),
    (36, "quan-jeans-ong-rong-xanh-nhat", "Quần jeans ống rộng xanh nhạt", "trousers", "Xanh nhạt", "Denim cotton", 959000, "Jeans xanh nhạt ống rộng thoải mái với đường may cổ điển."),
    (37, "quan-jogger-cotton-xam-nhat", "Quần jogger cotton xám nhạt", "trousers", "Xám nhạt", "Cotton pha polyester", 699000, "Jogger lưng thun và bo gấu mềm, hợp nhịp sống năng động."),
    (38, "quan-tay-ong-suong-xanh-navy", "Quần tây ống suông xanh navy", "trousers", "Xanh navy", "Polyester pha viscose", 979000, "Quần tây ly trước, phom suông chỉn chu và màu navy dễ phối."),
    (39, "quan-culottes-linen-den", "Quần culottes linen đen", "trousers", "Đen", "100% linen", 829000, "Culottes ống rộng lửng bằng linen thoáng mát cho ngày nắng."),
    (40, "quan-chino-ong-dung-xanh-reu", "Quần chino ống đứng xanh rêu", "trousers", "Xanh rêu", "Cotton twill", 839000, "Chino ống đứng bằng cotton twill, tông rêu trầm dễ phối."),
    (41, "giay-sneaker-retro-be-xanh", "Giày sneaker retro be xanh", "shoes", "Be xanh", "Da lộn pha vải, đế cao su", 1390000, "Sneaker dáng retro phối be và xanh sage với đế êm."),
    (42, "giay-mary-jane-da-den", "Giày Mary Jane da đen", "shoes", "Đen", "Da tổng hợp, đế cao su", 1190000, "Mary Jane quai mảnh, đế thấp gọn và bề mặt da mềm."),
    (43, "dep-quai-ngang-da-nau", "Dép quai ngang da nâu", "shoes", "Nâu", "Da bò, đế cao su", 790000, "Dép quai ngang da nâu tối giản, đế mềm cho ngày thư giãn."),
    (44, "giay-slip-on-canvas-xam", "Giày slip-on canvas xám", "shoes", "Xám than", "Canvas cotton, đế cao su", 749000, "Slip-on canvas xám dễ mang, đế trắng nhẹ cho ngày bận rộn."),
    (45, "sandal-quai-cheo-kem", "Sandal quai chéo màu kem", "shoes", "Kem", "Vải dệt, đế cao su", 699000, "Sandal quai chéo vải dệt mềm, màu kem sáng và đế phẳng."),
]

LEGACY_FOOTWEAR = {
    1: ("giay-chay-bo-nike-den", "Vải mesh, đế cao su"),
    2: ("giay-chay-bo-adidas-trang", "Vải mesh, đế cao su"),
    4: ("giay-the-thao-xanh", "Vải mesh, đế cao su"),
    6: ("giay-sneaker-trang", "Da tổng hợp, đế cao su"),
    11: ("giay-da-ngoai-xanh-reu", "Da tổng hợp, đế cao su"),
}
COLORS = {"black": "Đen", "white": "Trắng", "blue": "Xanh dương", "red": "Đỏ",
          "silver": "Bạc", "gold": "Vàng", "brown": "Nâu", "green": "Xanh rêu"}


def variants(product_id, color, sizes, total_stock):
    records = []
    for index, size in enumerate(sizes):
        stock = max(0, total_stock // len(sizes) + (1 if index < total_stock % len(sizes) else 0))
        records.append({"id": product_id * 100 + index + 1,
                        "sku": f"COGU-{product_id:03d}-{index + 1:02d}",
                        "color": color, "size": size, "stock": stock})
    return records


def main():
    old = json.loads(LEGACY.read_text(encoding="utf-8"))
    products = []
    for original in old:
        if original["category"] != "shoes":
            continue  # Preserve the legacy JSON fixture, but sell only clothing and footwear.
        slug, material = LEGACY_FOOTWEAR[original["id"]]
        sizes = ["38", "39", "40", "41", "42", "43"]
        color = COLORS[original["color"]]
        products.append({
            "id": original["id"], "slug": slug,
            "name_vi": original["name_vi"], "description_vi": original["description_vi"],
            "category": "shoes", "material": material,
            "price_vnd": original["price_vnd"], "image": original["image"],
            "is_new": bool(original.get("is_new")), "is_bestseller": bool(original.get("is_bestseller")),
            "images": [{"color": color, "image": original["image"]}],
            "variants": variants(original["id"], color, sizes, original["stock"]),
        })
    for product_id, slug, name, category, color, material, price, description in NEW:
        sizes = (["36", "37", "38", "39", "40", "41", "42"] if product_id in {42, 43, 45} else
                 ["38", "39", "40", "41", "42", "43"] if category == "shoes" else
                 ["28", "30", "32", "34"] if category == "trousers" else ["S", "M", "L", "XL"])
        image = f"images/catalog-{product_id}.png"
        item = {"id": product_id, "slug": slug, "name_vi": name,
                "description_vi": description, "category": category, "material": material,
                "price_vnd": price, "image": image, "is_new": product_id >= 24,
                "is_bestseller": product_id in {17, 19, 21, 26, 27},
                "images": [{"color": color, "image": image}],
                "variants": variants(product_id, color, sizes, 19 + product_id % 9)}
        if product_id == 17:
            item["images"].append({"color": "Trắng ngà", "image": "images/catalog-17-ivory.png"})
            item["variants"].extend([
                {"id": 1705, "sku": "COGU-017-05", "color": "Trắng ngà", "size": "S", "stock": 7},
                {"id": 1706, "sku": "COGU-017-06", "color": "Trắng ngà", "size": "M", "stock": 14},
                {"id": 1707, "sku": "COGU-017-07", "color": "Trắng ngà", "size": "L", "stock": 6},
                {"id": 1708, "sku": "COGU-017-08", "color": "Trắng ngà", "size": "XL", "stock": 0},
            ])
            item["variants"][2]["stock"] = 0  # Green L sold out; other combinations remain available.
        products.append(item)
    OUTPUT.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(products)} products and {sum(len(p['variants']) for p in products)} variants to {OUTPUT}")


if __name__ == "__main__":
    main()
