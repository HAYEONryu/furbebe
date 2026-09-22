import { Link } from 'react-router';

export function Button({ children, variant = 'primary', className = '', type = 'button', ...props }) {
  return <button type={type} className={`button ${variant === 'secondary' ? 'button-secondary' : ''} ${className}`} {...props}>{children}</button>;
}

export function ButtonLink({ children, variant = 'primary', className = '', ...props }) {
  return <Link className={`button ${variant === 'secondary' ? 'button-secondary' : ''} ${className}`} {...props}>{children}</Link>;
}
