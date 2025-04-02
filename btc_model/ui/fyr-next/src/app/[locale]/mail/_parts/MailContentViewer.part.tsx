import { createEditor, Descendant } from 'slate';
import React, { FC, useMemo } from 'react';
import { Editable, Slate, withReact } from 'slate-react';

interface MailContentViewerProps {
	content: Descendant[];
}
const MailContentViewerPart: FC<MailContentViewerProps> = (props) => {
	const { content } = props;

	const editor = useMemo(() => withReact(createEditor()), []);

	return (
		<Slate key={JSON.stringify(content)} editor={editor} initialValue={content}>
			<Editable readOnly placeholder='Enter some plain text...' />
		</Slate>
	);
};

export default MailContentViewerPart;
