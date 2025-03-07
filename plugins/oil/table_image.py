from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import base64

def draw(data: list):
    # 表格标题
    headers = ["城市", "92#", "95#", "98#", "柴油"]

    # 将数据转换为表格格式
    rows = []
    for city in data[0].keys():
        row = [city] + [str(data[i][city]) for i in range(len(data))]
        rows.append(row)

    # 图片尺寸和字体
    cell_width = 100
    cell_height = 40
    font_size = 20
    font = ImageFont.truetype("resource/font/DroidSansFallbackFull.ttf", font_size)  # 使用支持中文的字体文件

    # 计算图片尺寸
    image_width = cell_width * len(headers)
    image_height = cell_height * (len(rows) + 1)

    # 创建空白图片，背景为白色
    image = Image.new('RGB', (image_width, image_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # 绘制表格标题
    for i, header in enumerate(headers):
        x = i * cell_width
        y = 0
        # 绘制标题背景（灰色）
        draw.rectangle([x, y, x + cell_width, y + cell_height], fill="#F0F0F0")
        # 计算文字尺寸
        left, top, right, bottom = draw.textbbox((0, 0), header, font=font)
        text_width = right - left
        text_height = bottom - top
        # 计算居中位置
        text_x = x + (cell_width - text_width) / 2
        text_y = y + (cell_height - text_height) / 2
        # 绘制文字
        draw.text((text_x, text_y), header, fill="black", font=font)

    # 绘制表格内容
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            x = j * cell_width
            y = (i + 1) * cell_height
            # 绘制单元格背景（灰色）
            draw.rectangle([x, y, x + cell_width, y + cell_height], fill="#F0F0F0")
            # 计算文字尺寸
            left, top, right, bottom = draw.textbbox((0, 0), cell, font=font)
            text_width = right - left
            text_height = bottom - top
            # 计算居中位置
            text_x = x + (cell_width - text_width) / 2
            text_y = y + (cell_height - text_height) / 2
            # 绘制文字
            draw.text((text_x, text_y), cell, fill="black", font=font)

    # 绘制横线边框
    for i in range(len(rows) + 2):  # 包括标题行和内容行
        y = i * cell_height
        draw.line([0, y, image_width, y], fill="black")
    # 保存图片
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    # 转换为base64
    return base64.b64encode(img_byte_arr).decode()
