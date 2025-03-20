import asyncio

async def coroutine1():
    await asyncio.sleep(3)
    print("Coroutine 1 result")
    return "Coroutine 1 result"

async def coroutine2():
    await asyncio.sleep(1)
    print("Coroutine 2 result")
    return "Coroutine 2 result"

async def main():
    result1 = await coroutine1()
    result2 = await coroutine2()
    print(result1)
    print(result2)

asyncio.run(main())