# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFilter

def create_ximalaya_icon(size=1024):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # 1. 柔和投影 (Soft ambient shadow)
    shadow_offset_y = int(size * 0.035)
    shadow_blur = int(size * 0.045)
    pad = int(size * 0.08)
    radius = int(size * 0.22)

    shadow_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_img)
    s_box = (pad, pad + shadow_offset_y, size - pad, size - pad + shadow_offset_y)
    s_draw.rounded_rectangle(s_box, radius=radius, fill=(180, 40, 10, 85))
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(shadow_blur))
    img.alpha_composite(shadow_img)

    # 2. 喜马拉雅经典暖橙红渐变主板
    card_w = size - 2 * pad
    card_h = size - 2 * pad

    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    for y in range(card_h):
        for x in range(card_w):
            diag_t = (x * 0.4 + y * 0.6) / float(card_w * 0.4 + card_h * 0.6)
            # 丰富微质感渐变: 左上 #FF6A3D -> 中间 #F1381A -> 右下 #C81E0D
            cur_r = int(255 * (1 - diag_t) + 200 * diag_t)
            cur_g = int(106 * (1 - diag_t) + 30 * diag_t)
            cur_b = int(61 * (1 - diag_t) + 13 * diag_t)
            card.putpixel((x, y), (cur_r, cur_g, cur_b, 255))

    # 遮罩
    mask = Image.new("L", (card_w, card_h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle((0, 0, card_w, card_h), radius=radius, fill=255)

    # 3. 顶部微弱边框高光 (Glass outline highlight)
    top_highlight = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    th_draw = ImageDraw.Draw(top_highlight)
    th_draw.rounded_rectangle((2, 2, card_w - 2, card_h - 2), radius=radius - 2, outline=(255, 255, 255, 90), width=int(size * 0.008))

    card.putalpha(mask)
    card.alpha_composite(top_highlight)
    img.alpha_composite(card, (pad, pad))

    # 4. 纯净白色声波波峦 (Pure Solid White Soundwave Peaks)
    center_y = int(size * 0.48)
    
    # 7 根声波柱，形成经典的两座连绵山峰音律
    height_ratios = [0.35, 0.62, 0.96, 0.70, 0.88, 0.58, 0.32]
    bar_count = len(height_ratios)
    
    total_content_w = int(size * 0.48)
    max_content_h = int(size * 0.42)
    
    bar_w = int(total_content_w / (bar_count * 1.5))
    gap = int(bar_w * 0.5)
    actual_total_w = bar_count * bar_w + (bar_count - 1) * gap
    start_x = (size - actual_total_w) // 2 - int(size * 0.02) # 微偏左，给右下角徽标留出空间平衡

    fg_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    fg_draw = ImageDraw.Draw(fg_img)
    for i, h_ratio in enumerate(height_ratios):
        bh = int(max_content_h * h_ratio)
        bx0 = start_x + i * (bar_w + gap)
        bx1 = bx0 + bar_w
        by0 = center_y - bh // 2
        by1 = center_y + bh // 2
        r_bar = bar_w // 2
        fg_draw.rounded_rectangle((bx0, by0, bx1, by1), radius=r_bar, fill=(255, 255, 255, 255))

    # 5. 右下角下载角标 (Download Badge)
    badge_r = int(size * 0.125)
    badge_cx = int(size * 0.76)
    badge_cy = int(size * 0.75)
    
    # 角标阴影
    b_shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    b_sdraw = ImageDraw.Draw(b_shadow)
    b_sdraw.ellipse((badge_cx - badge_r, badge_cy - badge_r + int(size*0.015), badge_cx + badge_r, badge_cy + badge_r + int(size*0.015)), fill=(100, 20, 10, 110))
    b_shadow = b_shadow.filter(ImageFilter.GaussianBlur(int(size * 0.022)))
    img.alpha_composite(b_shadow)

    # 纯白底座 + 细致外环
    badge_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(badge_img)
    b_draw.ellipse((badge_cx - badge_r, badge_cy - badge_r, badge_cx + badge_r, badge_cy + badge_r), fill=(255, 255, 255, 255))
    
    # 箭头几何 (沉稳有力的红色下箭头)
    arrow_color = (228, 42, 18, 255)
    aw = int(badge_r * 0.42)
    ah = int(badge_r * 0.46)
    line_w = max(5, int(size * 0.018))

    # 箭头竖杆
    stem_top = badge_cy - int(ah * 0.8)
    stem_bottom = badge_cy + int(ah * 0.15)
    b_draw.rounded_rectangle((badge_cx - line_w // 2, stem_top, badge_cx + line_w // 2, stem_bottom), radius=line_w//2, fill=arrow_color)
    
    # 箭头三角
    tip_y = badge_cy + int(ah * 0.55)
    p1 = (badge_cx, tip_y)
    p2 = (badge_cx - aw, badge_cy + int(ah * 0.05))
    p3 = (badge_cx + aw, badge_cy + int(ah * 0.05))
    b_draw.polygon([p1, p2, p3], fill=arrow_color)
    
    # 底托托盘 (弧形圆角底线)
    bar_y0 = tip_y + int(size * 0.016)
    bar_y1 = bar_y0 + line_w
    b_draw.rounded_rectangle((badge_cx - aw, bar_y0, badge_cx + aw, bar_y1), radius=line_w//2, fill=arrow_color)

    # 合并图层
    img.alpha_composite(fg_img)
    img.alpha_composite(badge_img)

    return img

if __name__ == "__main__":
    icon_1024 = create_ximalaya_icon(1024)
    icon_1024.save("ximalaya-download/icon_preview.png", "PNG")

    # 包含 Windows 推荐的完整多级分辨率 ICO 格式
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    icon_1024.save("ximalaya-download/app.ico", format="ICO", sizes=sizes)
    print("New refined icon generated successfully!")
