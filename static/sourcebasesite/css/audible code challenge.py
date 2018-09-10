def braces(values):
	results = []
	stack = []
	set_open = {"{", "[", "("}
	dic = {"}": "{", "]": "[", ")": "("}
    for string in values:
    	for brack in string:
    		if len(stack) > 0:
    			if brack not in set_open and stack[-1] == dic[brack]:
    				stack.pop()
    			else:
    				stack.append(brack)
    		else:
    		stack.append(brack)
    	if stack:
    		results.append("NO")
    	else:
    		results.append("YES")
    return results

    {}[]()