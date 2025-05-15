import asyncio
import re
import uuid
from pathlib import Path
from typing import Optional

import filetype
from loguru import logger
from playwright.async_api import async_playwright, Page


class BrowserManager:
    """管理 Playwright 浏览器实例的封装类（异步版本）"""

    def __init__(self, cdp_url: str):
        """
        初始化浏览器管理器
        :param cdp_url: Chrome DevTools Protocol 地址
        """
        self.cdp_url = cdp_url
        self.playwright = None
        self.browser = None
        self.context = None
        self.conversation_page = {}

    async def __aenter__(self):
        """异步初始化浏览器实例"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_url)
        return self

    async def __aexit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """异步释放资源"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    def get_page(self, conversation_id: str) -> 'BrowserPage':
        return self.conversation_page.get(conversation_id)

    async def get_or_create_page(self, conversation_id: str,
                                 url: str = 'https://www.wenxiaobai.com/chat/tourist') -> 'BrowserPage':
        if self.conversation_page.get(conversation_id):
            return self.conversation_page.get(conversation_id)

        """创建新的页面管理器实例"""
        if not self.browser:
            raise RuntimeError("Browser not initialized")
        if not self.context:
            self.context = await self.browser.new_context(storage_state=Path(__file__).resolve().parent / "auth.json")
            self.context.set_default_timeout(10000)

        page = await self.context.new_page()

        # 监听页面关闭事件
        def handle_close():
            asyncio.create_task(self.close_callback(conversation_id))

        page.on('close', handle_close)

        logger.info(f"PlaywrightChat 创建新会话页: {conversation_id}")
        browser_page = BrowserPage(page)
        browser_page.conversation_id = conversation_id
        await browser_page.navigate(url)

        self.conversation_page[conversation_id] = browser_page
        return browser_page

    async def close_callback(self, conversation_id: str):
        """页面关闭时的回调处理"""
        if conversation_id in self.conversation_page:
            page = self.conversation_page[conversation_id]
            if page and not page.page.is_closed():
                await page.close()
                logger.info(f"PlaywrightChat 清理会话页: {conversation_id}")
            self.conversation_page.pop(conversation_id, None)

    async def close(self, conversation_id: str):
        """主动关闭指定会话页面"""
        await self.close_callback(conversation_id)


class BrowserPage:
    """管理页面操作和交互的封装类（异步版本）"""

    def __init__(self, browser_page: Page):
        self.page = browser_page
        self.conversation_id: Optional[str] = None
        self.is_ready = False

    async def navigate(self, url: str, timeout: int = 5 * 60 * 1000):
        """导航到指定URL"""
        await self.page.set_viewport_size({"width": 1366, "height": 800})
        await self.page.goto(url, timeout=timeout, wait_until="networkidle")
        await self.page.add_style_tag(content="* { animation: none !important; transition: none !important; }")
        await self.page.wait_for_timeout(3000)

    async def ready(self):
        if self.conversation_id and not self.is_ready:
            # 初始化页面
            await self.new_or_select_conversation(self.conversation_id)
            await self.changeModel("deepseekV3")
            await self.changeSearch("super_search")
            self.is_ready = True

    async def is_login(self):
        btn_count = await self.page.get_by_text("登录", exact=True).count()
        return btn_count == 0

    async def login(self, phone: str):
        """执行登录流程"""
        logger.info("PlaywrightChat 执行登录，发送验证码...")
        try:
            await self.page.get_by_text("登录", exact=True).click()
            await self.page.get_by_placeholder("请输入手机号").fill(phone)
            await self.page.locator(".ant-checkbox-input").click()
            await self.page.get_by_text("获取验证码", exact=True).click()
            return True
        except Exception as e:
            print(f"登录失败: {str(e)}")
            return False

    async def verify_login(self, verification_code: str):
        logger.info("PlaywrightChat 执行登录，确认验证码...")
        await self.page.get_by_placeholder("验证码").fill(verification_code)
        await self.page.get_by_text("确定", exact=True).click()
        await self.page.wait_for_url("https://www.wenxiaobai.com/chat/200006")
        await self.page.context.storage_state(path="auth.json")

    async def new_or_select_conversation(self, conversation_id: str, model: str = "deepseekV3",
                                         search_type: str = "no_search"):
        if not await self.is_login():
            return

        await self.open_conversation_tab()
        if not await self.has_conversation(conversation_id):
            logger.info(f"PlaywrightChat 新会话初始化，命名会话：{conversation_id}")
            # await self.page.get_by_alt_text('新对话').click()
            await self.page.keyboard.press('Control+K')
            await self.changeModel(model)
            await self.changeSearch(search_type)
            await self.sendMessage("你好")
            await self.getMessage()
            await self.page.wait_for_timeout(1000)
            await self.set_conversation_id(conversation_id)
        else:
            logger.info(f"PlaywrightChat 切换到会话：conversation_id={conversation_id}")
            await self.page.locator('#history-container-ID').get_by_text(
                conversation_id).first.click()

    async def open_conversation_tab(self):
        is_hide = (await self.page.locator('#dark-mode-container [class*=page_container_ellipsis]').count()) == 1
        if is_hide:
            await self.page.evaluate("""()=>document.querySelector(
                '#dark-mode-container [class^=EasySide_easy_container] svg'
            ).dispatchEvent(new MouseEvent("click", {bubbles: true,cancelable: true}));
            """)
            # await self.page.locator('#dark-mode-container [class^=page_ellipsis_ctl] svg').first.click()

    async def has_conversation(self, conversation_id: str):
        await self.page.locator('#history-container-ID').wait_for()
        c = await self.page.locator('#history-container-ID').get_by_text(conversation_id).count()
        return c > 0

    async def sendMessage(self, msg: str):
        logger.info(f"PlaywrightChat 发送消息：{msg}")
        await self.page.locator('[class*=MsgInput_input_main] [class*=MsgInput_input_textarea]').fill(msg)
        await self.page.wait_for_function("""()=>{
            selector = '[class*="MsgInput_input_main"] >:nth-child(3) >:nth-child(3)' 
            const button = document.querySelector(selector);
            return !button?.getAttribute('class')?.includes('MsgInput_disabled');
        }""", polling=500, timeout=1 * 60 * 1000)
        await self.page.locator('[class*="MsgInput_input_main"] >:nth-child(3) >:nth-child(3) svg').click()
        await self.page.wait_for_timeout(500)

    async def getMessage(self):
        logger.info(f"PlaywrightChat 等待消息中...")
        await self.page.locator('[class*="TurnCard_operation"] >[class*="TurnCard_left_opts"]') \
            .wait_for(timeout=5 * 60 * 1000)
        selector = '[class^=TurnCard_turn_container] .markdown-body .annotation_num'
        await self.page.evaluate(f"()=>document.querySelectorAll('{selector}').forEach(el => el.remove());")
        answer = await self.page.locator("[class^=TurnCard_turn_container] .markdown-body").first.text_content()
        return re.sub(r'\n{4,}', '\n\n\n', answer.replace(" 。", "。"))

    async def set_conversation_id(self, conversation_id: str):
        await self.open_conversation_tab()
        selector = '[class*=page_conversation_list] [class*=ConversationItem_active] [class^=ConversationItem_opt_btn_]'
        await self.page.evaluate(f"()=>document.querySelector('{selector}').style.display = 'block'")
        await self.page.locator(selector).first.click()
        await self.page.locator('.ant-popover').get_by_text('重命名', exact=True).filter(visible=True).click()
        selector = '[class*=page_conversation_list] [class*=ConversationItem_active] input'
        await self.page.fill(selector, conversation_id)
        await self.page.keyboard.press('Enter')


    async def getMarkdownMessage(self, conversation_id: str):
        await self.page.locator('[class*="TurnCard_operation"] >[class*="TurnCard_left_opts"]') \
            .wait_for(timeout=5 * 60 * 1000)
        await self.page.evaluate("""((conversation_id)=>{
                if(!document.originalExecCommand){
                    document.originalExecCommand = document.execCommand;
                    document.execCommand = function(command, showUI, value) {
                        if(command == 'copy') return false
                        return originalExecCommand.apply(this, arguments);
                    };
                    document[conversation_id] = ''
                    window.clipboardData={setData:(a,b)=>document[conversation_id]=b}
                }
            })
        """ + f"('{conversation_id}')")
        await self.page.locator('[class*="TurnCard_operation"] >[class*="TurnCard_left_opts"]').get_by_text(
            '复制').click()
        return await self.page.evaluate(f"()=>document.{conversation_id}")

    async def changeSearch(self, search_type: str = "super_search"):
        await self.page.locator(
            'xpath=//*[@data-key="no_search" or @data-key="quick_search" or @data-key="super_search"]').click()
        if not search_type or search_type == 'super_search':
            await self.page.get_by_role("tooltip").get_by_text('专业搜索').click()
        elif search_type == 'quick_search':
            await self.page.get_by_role("tooltip").get_by_text('日常搜索').click()
        else:
            await self.page.get_by_role("tooltip").get_by_text('不联网').click()

    async def changeModel(self, model: str = 'deepseekV3'):
        await self.page.locator('xpath=//*[@data-key="deepseekV3" or @data-key="deepseekR1"]').click()
        match model:
            case 'deepseekR1':
                await self.page.get_by_role("tooltip").get_by_text('深度思考（R1）').click()
            case 'qwen3':
                await self.page.get_by_role("tooltip").get_by_text('千问 3').click()
            case _:
                await self.page.get_by_role("tooltip").get_by_text('日常问答（V3）').click()

    async def get_content(self) -> str:
        """获取页面内容"""
        return await self.page.content()

    async def close(self):
        """关闭当前页面"""
        await self.page.close()

    async def delete_memory(self):
        await self.open_conversation_tab()
        selector = '[class*=page_conversation_list] [class*=ConversationItem_active] [class^=ConversationItem_opt_btn_]'
        await self.page.evaluate(f"()=>document.querySelector('{selector}').style.display = 'block'")
        await self.page.locator(selector).first.click()
        await self.page.locator('.ant-popover').get_by_text('删除', exact=True).filter(visible=True).click()

    async def upload_file(self, file_name, file_byte):
        logger.info(f"PlaywrightChat 上传文件：{file_name}")

        kind = filetype.guess(file_byte)
        file = {
            "name": file_name,
            "mimeType": kind.mime if kind else "application/octet-stream",
            "buffer": file_byte
        }
        # await self.page.set_input_files("#file-input", files=file)

        # 监听文件选择器弹出
        async with self.page.expect_file_chooser() as fc_info:
            await self.page.locator('[class*="MsgInput_input_main"] >:nth-child(3) >:nth-child(2) svg').click()
        file_chooser = await fc_info.value

        await file_chooser.set_files(file)

    async def upload_image(self, image_byte):
        kind = filetype.guess(image_byte)
        image_name = uuid.uuid4().hex + '.' + kind.extension if kind else 'jpeg'
        logger.info(f"PlaywrightChat 上传图片：{image_name}")

        file = {
            "name": image_name,
            "mimeType": kind.mime if kind else "application/octet-stream",
            "buffer": image_byte
        }

        # 监听文件选择器弹出
        async with self.page.expect_file_chooser() as fc_info:
            await self.page.locator('[class*="MsgInput_input_main"] >:nth-child(3) >:nth-child(1) svg').click()
        file_chooser = await fc_info.value

        await file_chooser.set_files(file)

    async def remove_thumb(self):
        if await self.page.locator('[class*="FileUpload_thumb_ctn"] span svg').count() == 1:
            await self.page.locator('[class*="FileUpload_thumb_ctn"] span svg').click()

async def main():
    # cdp_url = "ws://192.168.2.2:3000"
    # cdp_url = "ws://127.0.0.1:3000"
    cdp_url = "http://127.0.0.1:9222"
    async with BrowserManager(cdp_url=cdp_url) as browser_manager:
        # 创建第一个页面并登录
        wxid = "wxid_23232"
        page = await browser_manager.get_or_create_page(wxid)

        await page.new_or_select_conversation(wxid)
        await page.changeModel("deepseekV3")
        await page.changeSearch("super_search")

        while True:
            query = input("问题：")
            await page.sendMessage(query)
            answer = await page.getMessage()
            print(answer)
            try:
                await page.delete_memory()
            except Exception as e:
                logger.exception("错了错了", e)
                await page.page.screenshot(path="wenxiaobai.png")


if __name__ == "__main__":
    asyncio.run(main())
