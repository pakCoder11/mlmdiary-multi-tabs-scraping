from selenium_driverless import webdriver
import asyncio
async def main():
    async with webdriver.Chrome() as browser:

        # set the first context
        context_1 = browser.current_context
        # set the second context with a proxy
        context_2 = await browser.new_context()
        

        # visit the target page within each context
        await context_1.current_target.get("https://httpbin.io/ip")
        await context_2.get("https://httpbin.io/ip")

        # print the page source to view ip
        print(await context_1.page_source)
        print(await context_2.page_source)

# asyncio.run(main())

def delete_url_from_file(url_to_delete, file_path="links.txt"):
    """
    Delete a specific URL from the file.
    
    Args:
        url_to_delete (str): The URL to be deleted
        file_path (str): Path to the file containing URLs (default: links.txt)
    """
    try:
        # Read all URLs from file
        with open(file_path, 'r') as file:
            urls = file.readlines()
        
        # Clean URLs (remove whitespace/newlines)
        urls = [url.strip() for url in urls]
        
        # Check if URL exists in file
        if url_to_delete not in urls:
            print(f"URL {url_to_delete} not found in {file_path}")
            return
        
        # Remove the URL and rewrite the file
        urls.remove(url_to_delete)
        
        # # Write remaining URLs back to file
        with open(file_path, 'w') as file:
            for url in urls:
                file.write(f"{url}\n")
        print(f"Successfully removed {url_to_delete} from {file_path}")
            
    except FileNotFoundError:
        print(f"File {file_path} not found")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

# Example usage:
delete_url_from_file("https://www.mlmdiary.com/directory?page=85")